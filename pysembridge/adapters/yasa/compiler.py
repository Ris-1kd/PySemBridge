"""Compile Semantic Bridge IR into YASA external facts.

This adapter intentionally emits a neutral facts format first. A later YASA
BridgeFactLoader can consume this JSON and inject graph facts before taint
propagation.
"""

from __future__ import annotations

from typing import Any


def compile_bridge_to_yasa_facts(bridge: dict[str, Any]) -> dict[str, Any]:
    graph_facts = bridge.get("graph_facts", {})
    flow_facts = bridge.get("flow_facts", {})
    return {
        "version": "1.0",
        "source_bridge": bridge["bridge_id"],
        "project": bridge["project"],
        "language": bridge["language"],
        "gap_types": bridge["gap_types"],
        "yasa_injection": {
            "graph_facts": {
                "call_edges": graph_facts.get("call_edges", []),
                "type_facts": graph_facts.get("type_facts", []),
                "alias_facts": graph_facts.get("alias_facts", []),
                "callback_facts": graph_facts.get("callback_facts", []),
                "dynamic_class_facts": graph_facts.get("dynamic_class_facts", []),
            },
            "flow_facts": {
                "taint_transfers": flow_facts.get("taint_transfers", []),
                "container_transfers": flow_facts.get("container_transfers", []),
                "dict_key_transfers": flow_facts.get("dict_key_transfers", []),
                "string_transfers": flow_facts.get("string_transfers", []),
                "field_transfers": flow_facts.get("field_transfers", []),
            },
        },
        "validation": bridge.get("validation", {}),
        "evidence": bridge.get("evidence", []),
    }
