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
