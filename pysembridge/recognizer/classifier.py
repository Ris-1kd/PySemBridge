"""Classify extracted Python features into semantic bridge gap families."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from pysembridge.recognizer.features import FeatureHit


GAP_FAMILIES = {
    "dynamic_receiver_callgraph": {
        "dynamic_receiver_call",
        "dynamic_import",
        "decorator_control_flow",
        "framework_wrapper",
        "framework_registration",
        "factory_function",
        "plugin_registration",
        "async_task_schedule",
        "event_loop_dispatch",
    },
    "container_dict_key_flow": {
        "container_subscript",
        "dict_literal",
        "list_literal",
        "tuple_literal",
        "comprehension_flow",
        "dict_comprehension_flow",
        "generator_expression_flow",
    },
    "string_builder_flow": {
        "string_join_generator",
        "string_join_builder",
        "string_format_builder",
        "f_string_builder",
        "percent_string_format_builder",
        "string_concat_builder",
        "string_accumulator_builder",
    },
    "rebinding_platform_flow": {
        "function_rebinding",
        "alias_assignment",
        "conditional_binding",
        "conditional_import",
        "platform_branch",
        "monkey_patch_assignment",
    },
    "dynamic_attribute_protocol": {
        "dynamic_attribute_access",
        "special_method_protocol",
        "descriptor_property",
        "dynamic_method_injection",
    },
    "dynamic_class_metaprogramming": {
        "dynamic_type_construction",
        "factory_function",
        "metaclass_protocol",
        "dynamic_method_injection",
        "descriptor_property",
    },
    "callback_parser_dispatch": {
        "closure_callback",
        "nonlocal_closure_state",
        "callback_dict",
        "callback_container",
        "callback_argument",
        "higher_order_function",
        "async_function",
        "await_expression",
        "event_loop_dispatch",
    },
    "serialization_field_flow": {
        "deserialization",
        "descriptor_property",
    },
}


@dataclass(frozen=True)
class GapClassification:
    family: str
    score: int
    feature_counts: dict[str, int]
    representative_hits: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "score": self.score,
            "feature_counts": self.feature_counts,
            "representative_hits": self.representative_hits,
        }


def classify_features(hits: list[FeatureHit], top_k_hits: int = 5) -> list[GapClassification]:
    kind_counts = Counter(hit.kind for hit in hits)
    classifications: list[GapClassification] = []
    for family, feature_kinds in GAP_FAMILIES.items():
        score = sum(kind_counts[kind] for kind in feature_kinds)
        if score <= 0:
            continue
        reps = [hit.to_dict() for hit in hits if hit.kind in feature_kinds][:top_k_hits]
        classifications.append(
            GapClassification(
                family=family,
                score=score,
                feature_counts={kind: kind_counts[kind] for kind in sorted(feature_kinds) if kind_counts[kind]},
                representative_hits=reps,
            )
        )
    return sorted(classifications, key=lambda item: item.score, reverse=True)
