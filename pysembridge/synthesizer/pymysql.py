"""Bridge synthesis for PyMySQL-style dict-key and %-format query flows."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PymysqlPocFacts:
    source_function: str
    driver_function: str
    source_var: str
    dict_var: str
    query_var: str
    source_line: int
    dict_line: int
    query_line: int
    boundary_line: int
    boundary_expr: str


@dataclass(frozen=True)
class PymysqlMethodFacts:
    cursor_file: str
    execute_line: int
    mogrify_line: int
    escape_line: int
    format_line: int
    query_sink_line: int
    escape_expr: str
    format_expr: str
    query_sink_expr: str


def synthesize_pymysql_bridge(project_path: Path, project_name: str | None = None) -> dict[str, Any]:
    project_path = project_path.resolve()
    project = project_name or project_path.name
    poc = _find_poc(project_path)
    methods = _find_methods(project_path)

    return {
        "version": "1.0",
        "bridge_id": f"{_safe_id(project)}_dict_key_percent_format_auto",
        "language": "python",
        "project": project,
        "gap_types": ["receiver", "dict_key", "string_builder"],
        "scope": {
            "package": "pymysql",
            "function": "Cursor.execute/mogrify/_escape_args",
            "synthesizer": "pysembridge.synthesizer.pymysql",
        },
        "evidence": [
            {
                "kind": "source_to_dict_key",
                "location": {
                    "file": "poc/poc_cve_2024_36039_pymysql.py",
                    "line": poc.dict_line,
                    "expr": f"{poc.dict_var} = {{{poc.source_var}: ...}}",
                },
                "note": "The tainted source is used as a dictionary key.",
            },
            {
                "kind": "dict_key_to_escape_args",
                "location": {
                    "file": methods.cursor_file,
                    "line": methods.escape_line,
                    "expr": methods.escape_expr,
                },
                "note": "The dict comprehension preserves keys from args.items().",
            },
            {
                "kind": "percent_format_to_query",
                "location": {
                    "file": methods.cursor_file,
                    "line": methods.format_line,
                    "expr": methods.format_expr,
                },
                "note": "The query string is rebuilt by %-formatting with escaped args.",
            },
            {
                "kind": "query_to_sink",
                "location": {
                    "file": methods.cursor_file,
                    "line": methods.query_sink_line,
                    "expr": methods.query_sink_expr,
                },
                "note": "The formatted query is sent to _query.",
            },
        ],
        "graph_facts": {
            "type_facts": [
                {
                    "id": "auto_fake_cursor_type",
                    "variable": "FakeCursor()",
                    "scope": poc.driver_function,
                    "type": "pymysql.cursors.Cursor",
                    "reason": "FakeCursor inherits Cursor in the PoC.",
                }
            ],
            "call_edges": [
                {
                    "id": "auto_driver_to_cursor_execute",
                    "from": {
                        "file": "poc/poc_cve_2024_36039_pymysql.py",
                        "line": poc.boundary_line,
                        "function": poc.driver_function,
                        "expr": poc.boundary_expr,
                    },
                    "to": {
                        "file": methods.cursor_file,
                        "line": methods.execute_line,
                        "function": "Cursor.execute",
                    },
                    "reason": "The PoC calls FakeCursor().execute, inherited from Cursor.execute.",
                },
                {
                    "id": "auto_execute_to_mogrify",
                    "from": {
                        "file": methods.cursor_file,
                        "line": methods.mogrify_line,
                        "function": "Cursor.execute",
                        "expr": "self.mogrify(query, args)",
                    },
                    "to": {
                        "file": methods.cursor_file,
                        "line": methods.mogrify_line,
                        "function": "Cursor.mogrify",
                    },
                    "reason": "Cursor.execute delegates query construction to mogrify.",
                },
            ],
        },
        "flow_facts": {
            "dict_key_transfers": [
                {
                    "id": "auto_key_to_args_key",
                    "scope": poc.driver_function,
                    "from": {"expr": poc.source_var},
                    "to": {"expr": f"{poc.dict_var}.keys"},
                    "location": {
                        "file": "poc/poc_cve_2024_36039_pymysql.py",
                        "line": poc.dict_line,
                    },
                    "reason": "The tainted value is stored as a dict key.",
                },
                {
                    "id": "auto_args_key_to_escape_args_key",
                    "scope": "Cursor._escape_args",
                    "from": {"expr": "args.keys"},
                    "to": {"expr": "_escape_args.return.keys"},
                    "location": {"file": methods.cursor_file, "line": methods.escape_line},
                    "reason": "The dict comprehension preserves keys from args.items().",
                },
            ],
            "string_transfers": [
                {
                    "id": "auto_escape_keys_to_percent_format",
                    "scope": "Cursor.mogrify",
                    "from": {"expr": "_escape_args.return.keys"},
                    "to": {"expr": "query"},
                    "location": {"file": methods.cursor_file, "line": methods.format_line},
                    "reason": "Python %-formatting consults mapping keys while constructing the query string.",
                },
                {
                    "id": "auto_query_to_query_sink",
                    "scope": "Cursor.execute",
                    "from": {"expr": "query"},
                    "to": {"expr": "self._query.arg0"},
                    "location": {"file": methods.cursor_file, "line": methods.query_sink_line},
                    "reason": "The formatted query is passed to self._query.",
                },
            ],
        },
        "validation": {
            "expected_trace_suffix": [
                f"poc_cve_2024_36039_pymysql.py:{poc.boundary_line} {poc.boundary_expr}",
                f"cursors.py:{methods.escape_line} {methods.escape_expr}",
                f"cursors.py:{methods.format_line} {methods.format_expr}",
                f"cursors.py:{methods.query_sink_line} {methods.query_sink_expr}",
            ],
            "expected_sink": {
                "file": methods.cursor_file,
                "line": methods.query_sink_line,
                "function": "Cursor.execute",
                "expr": "self._query(...)",
            },
        },
    }


def _find_poc(project_path: Path) -> PymysqlPocFacts:
    poc_path = project_path / "poc" / "poc_cve_2024_36039_pymysql.py"
    text = poc_path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    source_function = next(n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and "source" in n.name)
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and "driver" in n.name]:
        source_var = ""
        source_line = -1
        dict_var = ""
        dict_line = -1
        query_var = ""
        query_line = -1
        boundary_line = -1
        boundary_expr = ""
        for stmt in func.body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call) and _call_name(stmt.value.func) == source_function:
                source_var = _single_target_name(stmt)
                source_line = stmt.lineno
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Dict) and source_var:
                if any(isinstance(key, ast.Name) and key.id == source_var for key in stmt.value.keys):
                    dict_var = _single_target_name(stmt)
                    dict_line = stmt.lineno
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                if "%(" in stmt.value.value:
                    query_var = _single_target_name(stmt)
                    query_line = stmt.lineno
            call = _return_call(stmt)
            if call and isinstance(call.func, ast.Attribute) and call.func.attr == "execute":
                boundary_line = stmt.lineno
                boundary_expr = ast.get_source_segment(text, call) or "FakeCursor().execute(query, args)"
        if source_var and dict_var and query_var and boundary_expr:
            return PymysqlPocFacts(
                source_function=source_function,
                driver_function=func.name,
                source_var=source_var,
                dict_var=dict_var,
                query_var=query_var,
                source_line=source_line,
                dict_line=dict_line,
                query_line=query_line,
                boundary_line=boundary_line,
                boundary_expr=boundary_expr,
            )
    raise ValueError("Could not synthesize PyMySQL PoC facts")


def _find_methods(project_path: Path) -> PymysqlMethodFacts:
    cursor_path = project_path / "pymysql" / "cursors.py"
    text = cursor_path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    relpath = str(cursor_path.relative_to(project_path))
    execute_line = mogrify_line = escape_line = format_line = query_sink_line = -1
    escape_expr = format_expr = query_sink_expr = ""

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name == "_escape_args":
            escape_line = node.lineno
            for child in ast.walk(node):
                if isinstance(child, ast.DictComp):
                    escape_expr = ast.get_source_segment(text, child) or "{key: ... for key, val in args.items()}"
                    break
        elif node.name == "mogrify":
            mogrify_line = node.lineno
            for child in ast.walk(node):
                if isinstance(child, ast.Assign) and isinstance(child.value, ast.BinOp) and isinstance(child.value.op, ast.Mod):
                    format_line = child.lineno
                    format_expr = ast.get_source_segment(text, child) or "query = query % self._escape_args(args, conn)"
                    break
        elif node.name == "execute":
            execute_line = node.lineno
            for child in ast.walk(node):
                if isinstance(child, ast.Assign) and isinstance(child.value, ast.Call):
                    if _call_name(child.value.func).endswith("mogrify"):
                        mogrify_line = child.lineno
                if isinstance(child, ast.Call) and _call_name(child.func) == "self._query":
                    query_sink_line = child.lineno
                    query_sink_expr = ast.get_source_segment(text, child) or "self._query(query)"

    if min(execute_line, mogrify_line, escape_line, format_line, query_sink_line) < 0:
        raise ValueError("Could not synthesize PyMySQL method facts")

    return PymysqlMethodFacts(
        cursor_file=relpath,
        execute_line=execute_line,
        mogrify_line=mogrify_line,
        escape_line=escape_line,
        format_line=format_line,
        query_sink_line=query_sink_line,
        escape_expr=escape_expr,
        format_expr=format_expr,
        query_sink_expr=query_sink_expr,
    )


def _single_target_name(stmt: ast.Assign) -> str:
    if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        return stmt.targets[0].id
    return ""


def _return_call(stmt: ast.stmt) -> ast.Call | None:
    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
        return stmt.value
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        return stmt.value
    return None


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    return ""


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower()
