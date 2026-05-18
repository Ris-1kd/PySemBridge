"""Template-based bridge synthesis for the pyload CVE benchmark shape."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceFile:
    path: Path
    relpath: str
    text: str
    tree: ast.AST


@dataclass(frozen=True)
class PocFacts:
    source_function: str
    driver_function: str
    receiver_name: str
    receiver_type: str
    source_var: str
    container_var: str
    container_index: int
    source_line: int
    container_line: int
    boundary_line: int
    boundary_expr: str
    target_method: str


@dataclass(frozen=True)
class MethodFacts:
    file: str
    class_name: str
    method_name: str
    method_line: int
    param_name: str
    extracted_expr: str
    string_var: str
    string_line: int
    string_expr: str
    sink_line: int
    sink_expr: str


def synthesize_pyload_bridge(project_path: Path, project_name: str | None = None) -> dict[str, Any]:
    project_path = project_path.resolve()
    poc = _find_poc_facts(project_path)
    method = _find_method_facts(project_path, poc.target_method)
    project = project_name or project_path.name

    return {
        "version": "1.0",
        "bridge_id": f"{_safe_id(project)}_receiver_container_string_auto",
        "language": "python",
        "project": project,
        "gap_types": ["receiver", "container", "string_builder"],
        "scope": {
            "package": "pyload",
            "function": f"{method.class_name}.{method.method_name}",
            "synthesizer": "pysembridge.synthesizer.pyload",
        },
        "evidence": [
            {
                "kind": "source_to_container",
                "location": {
                    "file": _relativize(poc_file(project_path), project_path),
                    "line": poc.container_line,
                    "expr": f"{poc.container_var} = [(..., {poc.source_var})]",
                },
                "note": f"The tainted value `{poc.source_var}` is stored in tuple/list index {poc.container_index}.",
            },
            {
                "kind": "container_to_string",
                "location": {
                    "file": method.file,
                    "line": method.string_line,
                    "expr": method.string_expr,
                },
                "note": f"The string builder extracts `{method.extracted_expr}` from `{method.param_name}`.",
            },
            {
                "kind": "string_to_sink",
                "location": {
                    "file": method.file,
                    "line": method.sink_line,
                    "expr": method.sink_expr,
                },
                "note": f"The sink call contains the constructed string `{method.string_var}`.",
            },
        ],
        "graph_facts": {
            "type_facts": [
                {
                    "id": "auto_receiver_type",
                    "variable": poc.receiver_name,
                    "scope": poc.driver_function,
                    "type": poc.receiver_type,
                    "reason": "Synthesized from the PoC function parameter annotation.",
                }
            ],
            "call_edges": [
                {
                    "id": "auto_boundary_to_method",
                    "from": {
                        "file": _relativize(poc_file(project_path), project_path),
                        "line": poc.boundary_line,
                        "function": poc.driver_function,
                        "expr": poc.boundary_expr,
                    },
                    "to": {
                        "file": method.file,
                        "line": method.method_line,
                        "function": f"{method.class_name}.{method.method_name}",
                    },
                    "reason": "Receiver type fact resolves the boundary call to the target method.",
                }
            ],
        },
        "flow_facts": {
            "container_transfers": [
                {
                    "id": "auto_source_to_container_index",
                    "scope": poc.driver_function,
                    "from": {"expr": poc.source_var},
                    "to": {"expr": f"{poc.container_var}[*][{poc.container_index}]"},
                    "location": {
                        "file": _relativize(poc_file(project_path), project_path),
                        "line": poc.container_line,
                    },
                    "reason": "Synthesized from a tuple/list literal that stores the source value.",
                },
                {
                    "id": "auto_container_index_to_generator",
                    "scope": f"{method.class_name}.{method.method_name}",
                    "from": {"expr": f"{method.param_name}[*][{poc.container_index}]"},
                    "to": {"expr": "generator.element"},
                    "location": {"file": method.file, "line": method.string_line},
                    "reason": f"Synthesized from generator extraction `{method.extracted_expr}`.",
                },
            ],
            "string_transfers": [
                {
                    "id": "auto_generator_to_string_builder",
                    "scope": f"{method.class_name}.{method.method_name}",
                    "from": {"expr": "generator.element"},
                    "to": {"expr": method.string_var},
                    "location": {"file": method.file, "line": method.string_line},
                    "reason": "Synthesized from str.join over a generator expression.",
                },
                {
                    "id": "auto_string_builder_to_sink_arg",
                    "scope": f"{method.class_name}.{method.method_name}",
                    "from": {"expr": method.string_var},
                    "to": {"expr": "self.c.execute.arg0"},
                    "location": {"file": method.file, "line": method.sink_line},
                    "reason": "Synthesized from an f-string argument passed to self.c.execute.",
                },
            ],
        },
        "validation": {
            "expected_trace_suffix": [
                f"{Path(_relativize(poc_file(project_path), project_path)).name}:{poc.boundary_line} {poc.boundary_expr}",
                f"{Path(method.file).name}:{method.string_line} {method.string_expr}",
                f"{Path(method.file).name}:{method.sink_line} self.c.execute(...)",
            ],
            "expected_sink": {
                "file": method.file,
                "line": method.sink_line,
                "function": f"{method.class_name}.{method.method_name}",
                "expr": "self.c.execute(...)",
            },
        },
    }


def _find_poc_facts(project_path: Path) -> PocFacts:
    source = _load_python_file(poc_file(project_path), project_path)
    imports = _collect_imports(source.tree)
    source_function = _find_source_function(source.tree)

    for node in ast.walk(source.tree):
        if not isinstance(node, ast.FunctionDef) or "driver" not in node.name:
            continue
        if not node.args.args:
            continue
        receiver = node.args.args[0]
        receiver_type = _annotation_name(receiver.annotation)
        receiver_type = imports.get(receiver_type, receiver_type)
        if not receiver_type:
            continue

        source_var = ""
        source_line = -1
        container_var = ""
        container_line = -1
        container_index = -1
        boundary_line = -1
        boundary_expr = ""
        target_method = ""

        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                call_name = _call_name(stmt.value.func)
                if call_name == source_function and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    source_var = stmt.targets[0].id
                    source_line = stmt.lineno
            if isinstance(stmt, ast.Assign) and source_var:
                found = _find_source_index_in_literal(stmt.value, source_var)
                if found is not None and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    container_var = stmt.targets[0].id
                    container_line = stmt.lineno
                    container_index = found
            call = _return_call(stmt)
            if call and isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
                if call.func.value.id == receiver.arg:
                    boundary_line = stmt.lineno
                    boundary_expr = ast.get_source_segment(source.text, call) or f"{receiver.arg}.{call.func.attr}(...)"
                    target_method = call.func.attr

        if all([source_var, container_var, target_method]) and container_index >= 0:
            return PocFacts(
                source_function=source_function,
                driver_function=node.name,
                receiver_name=receiver.arg,
                receiver_type=receiver_type,
                source_var=source_var,
                container_var=container_var,
                container_index=container_index,
                source_line=source_line,
                container_line=container_line,
                boundary_line=boundary_line,
                boundary_expr=boundary_expr,
                target_method=target_method,
            )

    raise ValueError("Could not synthesize PoC facts: no supported driver/source/container/boundary pattern found")


def _find_method_facts(project_path: Path, target_method: str) -> MethodFacts:
    for path in sorted(project_path.rglob("*.py")):
        source = _load_python_file(path, project_path)
        for class_node in [n for n in ast.walk(source.tree) if isinstance(n, ast.ClassDef)]:
            for func in [n for n in class_node.body if isinstance(n, ast.FunctionDef) and n.name == target_method]:
                param_name = func.args.args[1].arg if len(func.args.args) > 1 else "data"
                for stmt in func.body:
                    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
                        continue
                    extracted = _join_generator_subscript(stmt.value, param_name)
                    if not extracted:
                        continue
                    string_var = stmt.targets[0].id
                    sink = _find_execute_with_name(func, string_var, source.text)
                    if not sink:
                        continue
                    sink_line, sink_expr = sink
                    return MethodFacts(
                        file=source.relpath,
                        class_name=class_node.name,
                        method_name=func.name,
                        method_line=func.lineno,
                        param_name=param_name,
                        extracted_expr=extracted,
                        string_var=string_var,
                        string_line=stmt.lineno,
                        string_expr=ast.get_source_segment(source.text, stmt) or f"{string_var} = <join>",
                        sink_line=sink_line,
                        sink_expr=sink_expr,
                    )
    raise ValueError(f"Could not find supported target method pattern: {target_method}")


def poc_file(project_path: Path) -> Path:
    candidates = sorted((project_path / "poc").glob("*.py"))
    if candidates:
        return candidates[0]
    for candidate in sorted(project_path.rglob("poc*.py")):
        return candidate
    raise ValueError(f"No PoC Python file found under {project_path}")


def _load_python_file(path: Path, project_path: Path) -> SourceFile:
    text = path.read_text(encoding="utf-8")
    return SourceFile(path=path, relpath=_relativize(path, project_path), text=text, tree=ast.parse(text))


def _relativize(path: Path, project_path: Path) -> str:
    return str(path.resolve().relative_to(project_path.resolve()))


def _collect_imports(tree: ast.AST) -> dict[str, str]:
    imports: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return imports


def _find_source_function(tree: ast.AST) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and "source" in node.name:
            return node.name
    raise ValueError("No source function found in PoC")


def _annotation_name(annotation: ast.AST | None) -> str:
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        prefix = _annotation_name(annotation.value)
        return f"{prefix}.{annotation.attr}" if prefix else annotation.attr
    return ""


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = _call_name(func.value)
        return f"{base}.{func.attr}" if base else func.attr
    return ""


def _find_source_index_in_literal(node: ast.AST, source_var: str) -> int | None:
    tuples: list[ast.Tuple] = []
    if isinstance(node, ast.List):
        tuples.extend(item for item in node.elts if isinstance(item, ast.Tuple))
    elif isinstance(node, ast.Tuple):
        tuples.append(node)
    for tuple_node in tuples:
        for idx, elt in enumerate(tuple_node.elts):
            if isinstance(elt, ast.Name) and elt.id == source_var:
                return idx
    return None


def _return_call(stmt: ast.stmt) -> ast.Call | None:
    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
        return stmt.value
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        return stmt.value
    return None


def _join_generator_subscript(node: ast.AST, param_name: str) -> str:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "join":
        return ""
    if not node.args or not isinstance(node.args[0], ast.GeneratorExp):
        return ""
    gen = node.args[0]
    if not isinstance(gen.elt, ast.Subscript) or not gen.generators:
        return ""
    comp = gen.generators[0]
    if not isinstance(comp.iter, ast.Name) or comp.iter.id != param_name:
        return ""
    target_name = comp.target.id if isinstance(comp.target, ast.Name) else "x"
    index = _subscript_index(gen.elt)
    return f"{target_name}[{index}]"


def _subscript_index(node: ast.Subscript) -> str:
    slice_node = node.slice
    if isinstance(slice_node, ast.Index):  # Python 3.8 compatibility
        slice_node = slice_node.value
    if isinstance(slice_node, ast.Constant):
        return str(slice_node.value)
    if isinstance(slice_node, ast.Num):  # pragma: no cover
        return str(slice_node.n)
    return "?"


def _find_execute_with_name(func: ast.FunctionDef, name: str, source_text: str) -> tuple[int, str] | None:
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "execute":
            continue
        if _call_name(node.func.value) != "self.c":
            continue
        if not any(_contains_name(arg, name) for arg in node.args):
            continue
        return node.lineno, ast.get_source_segment(source_text, node) or "self.c.execute(...)"
    return None


def _contains_name(node: ast.AST, name: str) -> bool:
    return any(isinstance(child, ast.Name) and child.id == name for child in ast.walk(node))


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower()
