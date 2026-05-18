"""AST feature extraction for Python dynamic semantic gap recognition."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FeatureHit:
    kind: str
    file: str
    line: int
    expr: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "file": self.file,
            "line": self.line,
            "expr": self.expr,
            "detail": self.detail,
        }


def extract_python_features(project_path: Path, max_files: int = 2000) -> list[FeatureHit]:
    project_path = project_path.resolve()
    hits: list[FeatureHit] = []
    for idx, path in enumerate(sorted(project_path.rglob("*.py"))):
        if idx >= max_files:
            break
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        relpath = str(path.relative_to(project_path))
        visitor = _FeatureVisitor(relpath, text)
        visitor.visit(tree)
        hits.extend(visitor.hits)
    return hits


class _FeatureVisitor(ast.NodeVisitor):
    def __init__(self, relpath: str, text: str) -> None:
        self.relpath = relpath
        self.text = text
        self.hits: list[FeatureHit] = []
        self.branch_depth = 0
        self.try_depth = 0
        self.function_stack: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node.func)
        expr = ast.get_source_segment(self.text, node) or call_name

        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            self._add(
                "dynamic_receiver_call",
                node,
                expr,
                receiver=node.func.value.id,
                method=node.func.attr,
            )

        if _is_framework_registration_call(call_name):
            self._add("framework_registration", node, expr, callee=call_name)

        if _is_plugin_registration_call(call_name):
            self._add("plugin_registration", node, expr, callee=call_name)

        if _has_callable_argument(node):
            self._add("callback_argument", node, expr, callee=call_name)

        if call_name == "type" and len(node.args) >= 3:
            self._add("dynamic_type_construction", node, expr)

        if call_name in {"getattr", "setattr", "hasattr", "delattr"}:
            self._add(
                "dynamic_attribute_access",
                node,
                expr,
                builtin=call_name,
                dynamic_name=_argument_is_dynamic(node, 1),
            )

        if call_name in {"__import__", "importlib.import_module"} or call_name.endswith(".import_module"):
            self._add("dynamic_import", node, expr, callee=call_name)

        if isinstance(node.func, ast.Attribute) and node.func.attr == "join":
            if node.args and isinstance(node.args[0], ast.GeneratorExp):
                self._add("string_join_generator", node, expr)
            else:
                self._add("string_join_builder", node, expr)

        if isinstance(node.func, ast.Attribute) and node.func.attr in {"format", "format_map"}:
            self._add("string_format_builder", node, expr, method=node.func.attr)

        if call_name in {"map", "filter", "reduce", "sorted"}:
            self._add("higher_order_function", node, expr, callee=call_name)

        if call_name in {"asyncio.create_task", "asyncio.ensure_future"} or call_name.endswith(".create_task"):
            self._add("async_task_schedule", node, expr, callee=call_name)

        if call_name.endswith((".run_until_complete", ".call_soon", ".call_later", ".add_reader", ".add_writer")):
            self._add("event_loop_dispatch", node, expr, callee=call_name)

        if call_name in {"json.loads", "yaml.load", "pickle.loads"} or call_name.endswith((".loads", ".load")):
            self._add("deserialization", node, expr, callee=call_name)

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        expr = ast.get_source_segment(self.text, node) or "subscript"
        self._add("container_subscript", node, expr, index=_slice_expr(self.text, node.slice))
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        expr = ast.get_source_segment(self.text, node) or "dict"
        self._add("dict_literal", node, expr)
        if any(_looks_callable(value) for value in node.values):
            self._add("callback_dict", node, expr)
        self.generic_visit(node)

    def visit_List(self, node: ast.List) -> None:
        expr = ast.get_source_segment(self.text, node) or "list"
        self._add("list_literal", node, expr, element_count=len(node.elts))
        if any(_looks_callable(item) for item in node.elts):
            self._add("callback_container", node, expr)
        self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        expr = ast.get_source_segment(self.text, node) or "tuple"
        self._add("tuple_literal", node, expr, element_count=len(node.elts))
        if any(_looks_callable(item) for item in node.elts):
            self._add("callback_container", node, expr)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        expr = ast.get_source_segment(self.text, node) or "list comprehension"
        self._add("comprehension_flow", node, expr, comprehension="list")
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        expr = ast.get_source_segment(self.text, node) or "set comprehension"
        self._add("comprehension_flow", node, expr, comprehension="set")
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        expr = ast.get_source_segment(self.text, node) or "dict comprehension"
        self._add("dict_comprehension_flow", node, expr)
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        expr = ast.get_source_segment(self.text, node) or "generator expression"
        self._add("generator_expression_flow", node, expr)
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        expr = ast.get_source_segment(self.text, node) or "f-string"
        self._add("f_string_builder", node, expr)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        expr = ast.get_source_segment(self.text, node) or "binary operation"
        if isinstance(node.op, ast.Mod) and _string_like(node.left):
            self._add("percent_string_format_builder", node, expr)
        elif isinstance(node.op, ast.Add) and (_string_like(node.left) or _string_like(node.right)):
            self._add("string_concat_builder", node, expr)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        expr = ast.get_source_segment(self.text, node) or "assignment"
        if isinstance(node.value, ast.Lambda):
            self._add("function_rebinding", node, expr)
        if isinstance(node.value, (ast.Name, ast.Attribute)) and any(isinstance(t, ast.Name) for t in node.targets):
            self._add("alias_assignment", node, expr)
        if any(isinstance(t, ast.Attribute) for t in node.targets):
            self._add("monkey_patch_assignment", node, expr)
            if _looks_callable(node.value):
                self._add("dynamic_method_injection", node, expr)
        if self.branch_depth > 0 and _assignment_import_or_function_like(node):
            self._add("conditional_binding", node, expr)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        expr = ast.get_source_segment(self.text, node) or "augmented assignment"
        if isinstance(node.op, ast.Add):
            self._add("string_accumulator_builder", node, expr)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        expr = ast.get_source_segment(self.text, node.test) or "if"
        names = {_name.id for _name in ast.walk(node.test) if isinstance(_name, ast.Name)}
        if names.intersection({"sys", "os", "platform"}) or _contains_platform_attr(node.test):
            self._add("platform_branch", node, expr)
        self.branch_depth += 1
        self.generic_visit(node)
        self.branch_depth -= 1

    def visit_Import(self, node: ast.Import) -> None:
        expr = ast.get_source_segment(self.text, node) or "import"
        if self.branch_depth > 0 or self.try_depth > 0:
            self._add("conditional_import", node, expr)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        expr = ast.get_source_segment(self.text, node) or "from import"
        if self.branch_depth > 0 or self.try_depth > 0:
            self._add("conditional_import", node, expr, module=node.module or "")
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self.try_depth += 1
        self.generic_visit(node)
        self.try_depth -= 1

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.keywords or node.bases:
            for base in node.bases:
                base_name = _call_name(base)
                if base_name in {"type", "ABCMeta"} or base_name.endswith("Meta"):
                    self._add("metaclass_protocol", node, f"class {node.name}", base=base_name)
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name.startswith("__") and item.name.endswith("__"):
                self._add(
                    "special_method_protocol",
                    item,
                    f"class {node.name}.{item.name}",
                    class_name=node.name,
                    method=item.name,
                )
            if isinstance(item, ast.FunctionDef):
                for deco in item.decorator_list:
                    deco_name = _call_name(deco.func) if isinstance(deco, ast.Call) else _call_name(deco)
                    if deco_name in {"property", "cached_property"} or deco_name.endswith(".setter"):
                        self._add("descriptor_property", item, f"{node.name}.{item.name}", decorator=deco_name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        for deco in node.decorator_list:
            deco_expr = ast.get_source_segment(self.text, deco) or _call_name(deco)
            self._add("decorator_control_flow", node, f"@{deco_expr}", function=node.name)
            if _is_framework_decorator(deco_expr):
                self._add("framework_wrapper", node, f"@{deco_expr}", function=node.name)
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                self._add("closure_callback", child, f"nested function {child.name}", parent=node.name)
        if _returns_function_or_class(node):
            self._add("factory_function", node, f"def {node.name}", function=node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        self._add("async_function", node, f"async def {node.name}", function=node.name)
        for deco in node.decorator_list:
            deco_expr = ast.get_source_segment(self.text, deco) or _call_name(deco)
            self._add("decorator_control_flow", node, f"@{deco_expr}", function=node.name)
            if _is_framework_decorator(deco_expr):
                self._add("framework_wrapper", node, f"@{deco_expr}", function=node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Await(self, node: ast.Await) -> None:
        expr = ast.get_source_segment(self.text, node) or "await"
        self._add("await_expression", node, expr)
        self.generic_visit(node)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self._add("nonlocal_closure_state", node, f"nonlocal {', '.join(node.names)}", names=node.names)
        self.generic_visit(node)

    def _add(self, kind: str, node: ast.AST, expr: str, **detail: Any) -> None:
        self.hits.append(
            FeatureHit(
                kind=kind,
                file=self.relpath,
                line=getattr(node, "lineno", 1),
                expr=expr,
                detail=detail,
            )
        )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    return ""


def _is_framework_registration_call(call_name: str) -> bool:
    method = call_name.rsplit(".", 1)[-1]
    return method in {
        "route",
        "add_route",
        "add_url_rule",
        "middleware",
        "on_event",
        "add_event_handler",
        "register_blueprint",
        "include_router",
    }


def _is_framework_decorator(expr: str) -> bool:
    return any(token in expr for token in (".route", ".middleware", ".on_event", "router.", "app."))


def _is_plugin_registration_call(call_name: str) -> bool:
    method = call_name.rsplit(".", 1)[-1]
    return method in {
        "register",
        "unregister",
        "add_plugin",
        "load_plugin",
        "entry_points",
        "hookimpl",
        "connect",
        "signal",
    }


def _has_callable_argument(node: ast.Call) -> bool:
    return any(_looks_callable(arg) for arg in [*node.args, *(kw.value for kw in node.keywords)])


def _looks_callable(node: ast.AST | None) -> bool:
    if node is None:
        return False
    if isinstance(node, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return True
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.Attribute):
        return True
    return False


def _argument_is_dynamic(node: ast.Call, index: int) -> bool:
    if len(node.args) <= index:
        return False
    arg = node.args[index]
    return not isinstance(arg, ast.Constant)


def _slice_expr(text: str, node: ast.AST) -> str:
    if isinstance(node, ast.Index):  # Python 3.8 compatibility
        node = node.value
    return ast.get_source_segment(text, node) or "?"


def _string_like(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, ast.JoinedStr):
        return True
    return False


def _contains_platform_attr(node: ast.AST) -> bool:
    names = {_call_name(child) for child in ast.walk(node)}
    return any(
        name.startswith(("sys.", "os.", "platform.")) or name in {"sys", "os", "platform"} for name in names
    )


def _assignment_import_or_function_like(node: ast.Assign) -> bool:
    return isinstance(node.value, (ast.Name, ast.Attribute, ast.Call, ast.Lambda))


def _returns_function_or_class(node: ast.FunctionDef) -> bool:
    nested_names = {child.name for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    for child in ast.walk(node):
        if isinstance(child, ast.Return):
            if isinstance(child.value, ast.Name) and child.value.id in nested_names:
                return True
            if isinstance(child.value, ast.Lambda):
                return True
            if isinstance(child.value, ast.Call) and _call_name(child.value.func) == "type":
                return True
    return False
