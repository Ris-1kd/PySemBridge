"""Generic Semantic Bridge synthesis pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pysembridge.recognizer.classifier import GapClassification, classify_features
from pysembridge.recognizer.features import FeatureHit, extract_python_features
from pysembridge.synthesizer.pyload import synthesize_pyload_bridge
from pysembridge.synthesizer.pymysql import synthesize_pymysql_bridge


@dataclass(frozen=True)
class AutoSynthesisResult:
    project: str
    features: list[FeatureHit]
    classifications: list[GapClassification]
    bridges: list[dict[str, Any]]
    gap_specs: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "feature_count": len(self.features),
            "classifications": [item.to_dict() for item in self.classifications],
            "bridges": self.bridges,
            "gap_specs": self.gap_specs,
        }


def synthesize_auto(project_path: Path, project_name: str | None = None) -> AutoSynthesisResult:
    project_path = project_path.resolve()
    project = project_name or project_path.name
    features = extract_python_features(project_path)
    classifications = classify_features(features)

    bridges: list[dict[str, Any]] = []
    gap_specs = [_classification_to_gap_spec(project, classification) for classification in classifications]

    if _looks_like_pyload_pattern(classifications):
        try:
            bridges.append(synthesize_pyload_bridge(project_path, project))
        except Exception as exc:  # Keep generic classification useful if concrete synthesis fails.
            gap_specs.append(
                {
                    "project": project,
                    "family": "dynamic_receiver_container_string_concrete_synthesis_failed",
                    "status": "needs_review",
                    "reason": str(exc),
                }
            )

    if _looks_like_pymysql_pattern(project_path, classifications):
        try:
            bridges.append(synthesize_pymysql_bridge(project_path, project))
        except Exception as exc:
            gap_specs.append(
                {
                    "project": project,
                    "family": "dict_key_percent_format_concrete_synthesis_failed",
                    "status": "needs_review",
                    "reason": str(exc),
                }
            )

    return AutoSynthesisResult(
        project=project,
        features=features,
        classifications=classifications,
        bridges=bridges,
        gap_specs=gap_specs,
    )


def scan_project_gaps(
    project_path: Path,
    project_name: str | None = None,
    *,
    include_features: bool = False,
) -> dict[str, Any]:
    """Scan an arbitrary Python project for dynamic semantic gap candidates.

    This mode deliberately does not synthesize CVE-specific executable bridges.
    It is intended for source-only project mining: find Python dynamic features
    that are likely to require semantic bridge facts if taint propagation later
    breaks through them.
    """

    project_path = project_path.resolve()
    project = project_name or project_path.name
    features = extract_python_features(project_path)
    classifications = classify_features(features)
    gap_specs = [_classification_to_gap_spec(project, classification) for classification in classifications]
    result: dict[str, Any] = {
        "version": "0.1",
        "mode": "source_only_dynamic_gap_scan",
        "project": project,
        "project_path": str(project_path),
        "requires_cve": False,
        "requires_poc": False,
        "requires_source_sink": False,
        "feature_count": len(features),
        "gap_count": len(gap_specs),
        "gap_specs": gap_specs,
    }
    if include_features:
        result["features"] = [feature.to_dict() for feature in features]
    return result


def synthesize_generic_bridge(
    project_path: Path,
    project_name: str | None = None,
    *,
    max_facts_per_family: int = 5,
) -> dict[str, Any]:
    """Synthesize a generic, source-only Semantic Bridge IR from gap candidates.

    The result is intentionally hypothesis-level: every generated fact is
    evidence-scoped and marked in its reason as requiring analyzer validation.
    It is suitable for adapter compilation and iterative refinement, but it is
    not a claim that a vulnerability exists.
    """

    project_path = project_path.resolve()
    project = project_name or project_path.name
    features = extract_python_features(project_path)
    classifications = classify_features(features)

    gap_types = sorted(
        {
            gap_type
            for classification in classifications
            for gap_type in _gap_types_for_family(classification.family)
        }
    )
    if not gap_types:
        gap_types = ["field"]

    graph_facts: dict[str, list[dict[str, Any]]] = {
        "call_edges": [],
        "type_facts": [],
        "alias_facts": [],
        "callback_facts": [],
        "dynamic_class_facts": [],
    }
    flow_facts: dict[str, list[dict[str, Any]]] = {
        "taint_transfers": [],
        "container_transfers": [],
        "dict_key_transfers": [],
        "string_transfers": [],
        "field_transfers": [],
    }
    evidence: list[dict[str, Any]] = []

    for classification in classifications:
        for index, hit in enumerate(classification.representative_hits[:max_facts_per_family], start=1):
            evidence.append(_hit_to_evidence(classification.family, hit))
            _append_generic_fact(
                project=project,
                family=classification.family,
                hit=hit,
                index=index,
                graph_facts=graph_facts,
                flow_facts=flow_facts,
            )

    return {
        "version": "1.0",
        "bridge_id": f"{_safe_id(project)}_generic_dynamic_semantics",
        "language": "python",
        "project": project,
        "gap_types": gap_types,
        "scope": {
            "mode": "source_only",
            "project_root": str(project_path),
            "hypothesis_level": "candidate",
            "requires_analyzer_validation": True,
        },
        "evidence": evidence,
        "graph_facts": graph_facts,
        "flow_facts": flow_facts,
        "validation": {
            "requires_source_sink_query": True,
            "requires_analyzer_rerun": True,
            "intended_workflow": [
                "compile this IR with an analyzer adapter",
                "rerun the static analyzer with normal source/sink rules",
                "keep facts that improve trace completeness",
                "refine or discard facts that do not affect the trace or create false positives",
            ],
        },
    }


def _looks_like_pyload_pattern(classifications: list[GapClassification]) -> bool:
    families = {item.family for item in classifications}
    return {
        "dynamic_receiver_callgraph",
        "container_dict_key_flow",
        "string_builder_flow",
    }.issubset(families)


def _looks_like_pymysql_pattern(project_path: Path, classifications: list[GapClassification]) -> bool:
    families = {item.family for item in classifications}
    if not {"container_dict_key_flow", "string_builder_flow", "dynamic_receiver_callgraph"}.issubset(families):
        return False
    return (project_path / "pymysql" / "cursors.py").exists()


def _classification_to_gap_spec(project: str, classification: GapClassification) -> dict[str, Any]:
    return {
        "project": project,
        "family": classification.family,
        "status": "candidate",
        "repair_layer": _repair_layer(classification.family),
        "feature_counts": classification.feature_counts,
        "representative_hits": classification.representative_hits,
        "bridge_actions": _bridge_actions(classification.family),
        "candidate_semantic_facts": _candidate_semantic_facts(classification.family, classification.representative_hits),
    }


def _repair_layer(family: str) -> str:
    if family in {"dynamic_receiver_callgraph", "callback_parser_dispatch"}:
        return "graph_facts.call_edges/callback_facts"
    if family in {"container_dict_key_flow", "string_builder_flow", "serialization_field_flow"}:
        return "flow_facts"
    if family in {"rebinding_platform_flow", "dynamic_attribute_protocol", "dynamic_class_metaprogramming"}:
        return "graph_facts + flow_facts"
    return "unknown"


def _bridge_actions(family: str) -> list[str]:
    actions = {
        "dynamic_receiver_callgraph": [
            "infer receiver type facts",
            "add missing dynamic call edges",
            "preserve boundary call as bridge evidence",
        ],
        "container_dict_key_flow": [
            "add element/index/key taint transfer facts",
            "track list/tuple/dict literal construction",
            "track subscript extraction",
        ],
        "string_builder_flow": [
            "add str.join/format/f-string transfer facts",
            "connect constructed string to sink argument",
        ],
        "rebinding_platform_flow": [
            "resolve alias/rebinding candidates",
            "select feasible platform branch or emit guarded alternatives",
        ],
        "dynamic_attribute_protocol": [
            "resolve getattr/setattr/descriptor/special-method protocol edges",
            "add object field transfer facts",
        ],
        "dynamic_class_metaprogramming": [
            "recover type(...) or class-factory generated class facts",
            "add dynamically injected method edges",
            "connect descriptor/metaclass protocol calls to implementation methods",
        ],
        "callback_parser_dispatch": [
            "recover callback registration-to-invocation edges",
            "add closure captured variable transfers",
        ],
        "serialization_field_flow": [
            "connect parsed object/dict fields to attributes",
            "add field/index transfer facts after deserialization",
        ],
    }
    return actions.get(family, [])


def _gap_types_for_family(family: str) -> list[str]:
    mapping = {
        "dynamic_receiver_callgraph": ["receiver"],
        "container_dict_key_flow": ["container", "dict_key"],
        "string_builder_flow": ["string_builder"],
        "rebinding_platform_flow": ["rebinding"],
        "dynamic_attribute_protocol": ["getattr", "special_method", "field"],
        "dynamic_class_metaprogramming": ["dynamic_class"],
        "callback_parser_dispatch": ["callback_parser", "closure"],
        "serialization_field_flow": ["field"],
    }
    return mapping.get(family, ["field"])


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_") or "project"


def _location_from_hit(hit: dict[str, Any]) -> dict[str, Any]:
    location = {
        "file": str(hit.get("file", "")),
        "line": int(hit.get("line", 1) or 1),
    }
    expr = hit.get("expr")
    if expr:
        location["expr"] = str(expr)
    return location


def _hit_to_evidence(family: str, hit: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": family,
        "location": _location_from_hit(hit),
        "note": (
            f"Source-only scan found {hit.get('kind', 'dynamic feature')} as a "
            "candidate Python dynamic semantic gap. This evidence requires "
            "analyzer validation before it is accepted as a bridge."
        ),
    }


def _append_generic_fact(
    *,
    project: str,
    family: str,
    hit: dict[str, Any],
    index: int,
    graph_facts: dict[str, list[dict[str, Any]]],
    flow_facts: dict[str, list[dict[str, Any]]],
) -> None:
    detail = hit.get("detail", {})
    kind = str(hit.get("kind", "feature"))
    fact_id = f"{_safe_id(project)}_{_safe_id(family)}_{index}_{_safe_id(kind)}"
    loc = _location_from_hit(hit)
    expr = str(hit.get("expr", ""))
    reason = (
        "Generated from source-only dynamic gap scan. This is a candidate "
        "semantic bridge fact and must be validated by analyzer rerun."
    )

    if family == "dynamic_receiver_callgraph":
        receiver = detail.get("receiver")
        method = detail.get("method") or detail.get("callee") or expr
        graph_facts["type_facts"].append(
            {
                "id": f"{fact_id}_receiver_type",
                "variable": str(receiver or "<receiver>"),
                "scope": str(hit.get("file", "")),
                "type": "unknown_runtime_receiver_type",
                "reason": reason,
            }
        )
        graph_facts["call_edges"].append(
            {
                "id": f"{fact_id}_call_edge",
                "from": loc,
                "to": {"expr": f"<dynamic-dispatch:{method}>"},
                "reason": reason,
            }
        )
    elif family == "container_dict_key_flow":
        target = "dict_key_transfers" if kind in {"dict_literal", "dict_comprehension_flow"} else "container_transfers"
        flow_facts[target].append(
            {
                "id": fact_id,
                "scope": str(hit.get("file", "")),
                "from": {"expr": f"{expr}.element_or_key"},
                "to": {"expr": expr, "index_or_key": detail.get("index")},
                "location": loc,
                "reason": reason,
            }
        )
    elif family == "string_builder_flow":
        flow_facts["string_transfers"].append(
            {
                "id": fact_id,
                "scope": str(hit.get("file", "")),
                "from": {"expr": f"{expr}.operands"},
                "to": {"expr": expr},
                "location": loc,
                "reason": reason,
            }
        )
    elif family == "callback_parser_dispatch":
        graph_facts["callback_facts"].append(
            {
                "id": fact_id,
                "register": loc,
                "trigger": {"expr": "<framework-or-callback-trigger>"},
                "target": {"expr": expr or "<callback-target>"},
                "captures": [],
                "reason": reason,
            }
        )
    elif family == "rebinding_platform_flow":
        graph_facts["alias_facts"].append(
            {
                "id": fact_id,
                "name": expr or "<alias>",
                "targets": ["<runtime-selected-target>"],
                "reason": reason,
            }
        )
    elif family == "dynamic_class_metaprogramming":
        graph_facts["dynamic_class_facts"].append(
            {
                "id": fact_id,
                "factory": expr or "<dynamic-class-factory>",
                "created_at": loc,
                "methods": {},
                "reason": reason,
            }
        )
    elif family in {"dynamic_attribute_protocol", "serialization_field_flow"}:
        flow_facts["field_transfers"].append(
            {
                "id": fact_id,
                "scope": str(hit.get("file", "")),
                "from": {"expr": f"{expr}.input"},
                "to": {"expr": f"{expr}.field_or_attribute"},
                "location": loc,
                "reason": reason,
            }
        )
    else:
        flow_facts["taint_transfers"].append(
            {
                "id": fact_id,
                "scope": str(hit.get("file", "")),
                "from": {"expr": f"{expr}.input"},
                "to": {"expr": f"{expr}.output"},
                "location": loc,
                "reason": reason,
            }
        )


def _candidate_semantic_facts(family: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for hit in hits:
        detail = hit.get("detail", {})
        base = {
            "evidence": {
                "file": hit.get("file"),
                "line": hit.get("line"),
                "expr": hit.get("expr"),
                "kind": hit.get("kind"),
            },
            "confidence": "candidate",
            "needs_validation": True,
        }
        if family == "dynamic_receiver_callgraph":
            fact = {
                **base,
                "fact_type": "possible_call_edge_or_receiver_type",
                "from_expr": hit.get("expr"),
                "receiver": detail.get("receiver"),
                "method": detail.get("method") or detail.get("callee"),
                "bridge_hint": "Resolve the receiver's runtime type and add a guarded call edge if static dispatch misses this call.",
            }
        elif family == "container_dict_key_flow":
            fact = {
                **base,
                "fact_type": "possible_container_transfer",
                "container_expr": hit.get("expr"),
                "index_or_key": detail.get("index"),
                "bridge_hint": "Propagate taint between container elements, subscripts, comprehensions, and extracted values.",
            }
        elif family == "string_builder_flow":
            fact = {
                **base,
                "fact_type": "possible_string_builder_transfer",
                "builder_expr": hit.get("expr"),
                "bridge_hint": "Propagate taint from formatted/joined/concatenated operands to the constructed string.",
            }
        elif family == "callback_parser_dispatch":
            fact = {
                **base,
                "fact_type": "possible_callback_edge",
                "callback_expr": hit.get("expr"),
                "callee": detail.get("callee"),
                "bridge_hint": "Connect callback registration or callable argument to the eventual invocation site.",
            }
        elif family == "rebinding_platform_flow":
            fact = {
                **base,
                "fact_type": "possible_alias_or_rebinding",
                "binding_expr": hit.get("expr"),
                "bridge_hint": "Resolve guarded aliases, conditional imports, monkey patches, or platform-specific bindings.",
            }
        elif family == "dynamic_attribute_protocol":
            fact = {
                **base,
                "fact_type": "possible_attribute_or_protocol_transfer",
                "attribute_expr": hit.get("expr"),
                "bridge_hint": "Model getattr/setattr, descriptor/property, injected method, or special-method protocol behavior.",
            }
        elif family == "dynamic_class_metaprogramming":
            fact = {
                **base,
                "fact_type": "possible_dynamic_class_fact",
                "class_expr": hit.get("expr"),
                "bridge_hint": "Recover generated class/type facts and dynamically attached methods.",
            }
        elif family == "serialization_field_flow":
            fact = {
                **base,
                "fact_type": "possible_deserialization_field_transfer",
                "parser_expr": hit.get("expr"),
                "bridge_hint": "Propagate taint from serialized input through parsed object fields or dict keys.",
            }
        else:
            fact = {
                **base,
                "fact_type": "possible_semantic_gap",
                "bridge_hint": "Review this dynamic feature and add scoped graph or flow facts if analyzer propagation breaks here.",
            }
        facts.append(fact)
    return facts
