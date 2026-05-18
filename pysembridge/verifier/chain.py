"""Semantic Bridge chain verification helpers."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChainVerification:
    ok: bool
    source: str
    sink: str
    path: list[str]
    missing: list[str]
    call_edges: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "source": self.source,
            "sink": self.sink,
            "path": self.path,
            "missing": self.missing,
            "call_edges": self.call_edges,
        }


def verify_bridge_chain(bridge: dict[str, Any], source_expr: str, sink_expr: str) -> ChainVerification:
    edges: dict[str, list[str]] = {}
    missing: list[str] = []

    flow_facts = bridge.get("flow_facts", {})
    for group_name, transfers in flow_facts.items():
        if not isinstance(transfers, list):
            continue
        for transfer in transfers:
            from_expr = transfer.get("from", {}).get("expr")
            to_expr = transfer.get("to", {}).get("expr")
            if from_expr and to_expr:
                edges.setdefault(from_expr, []).append(to_expr)
            else:
                missing.append(f"{group_name}:{transfer.get('id', '<unknown>')}")

    path = _find_path(edges, source_expr, sink_expr)

    call_edges = []
    for edge in bridge.get("graph_facts", {}).get("call_edges", []):
        from_loc = edge.get("from", {})
        to_loc = edge.get("to", {})
        call_edges.append(
            f"{from_loc.get('file')}:{from_loc.get('line')} {from_loc.get('expr')}"
            f" -> {to_loc.get('file')}:{to_loc.get('line')} {to_loc.get('function')}"
        )

    if not call_edges:
        missing.append("graph_facts.call_edges")

    return ChainVerification(
        ok=bool(path) and bool(call_edges) and not missing,
        source=source_expr,
        sink=sink_expr,
        path=path,
        missing=missing,
        call_edges=call_edges,
    )


def _find_path(edges: dict[str, list[str]], source: str, sink: str) -> list[str]:
    queue: deque[tuple[str, list[str]]] = deque([(source, [source])])
    seen = {source}

    while queue:
        current, path = queue.popleft()
        if current == sink:
            return path
        for nxt in edges.get(current, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            queue.append((nxt, path + [nxt]))
    return []
