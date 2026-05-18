"""SARIF trace verification for PySemBridge tool runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SarifVerification:
    ok: bool
    sarif: str
    expected_sink: str
    result_count: int
    enhanced_result_count: int
    matched_result_index: int | None
    trace_steps: list[str]
    missing: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "sarif": self.sarif,
            "expected_sink": self.expected_sink,
            "result_count": self.result_count,
            "enhanced_result_count": self.enhanced_result_count,
            "matched_result_index": self.matched_result_index,
            "trace_steps": self.trace_steps,
            "missing": self.missing,
        }


def verify_sarif_trace(
    sarif_path: Path,
    expected_sink: str,
    expected_trace_contains: list[str] | None = None,
    require_enhanced: bool = True,
) -> SarifVerification:
    sarif_path = sarif_path.resolve()
    obj = json.loads(sarif_path.read_text(encoding="utf-8"))
    results = obj.get("runs", [{}])[0].get("results", [])
    expected_trace_contains = expected_trace_contains or []

    enhanced_results = [result for result in results if result.get("semanticBridgeEnhanced") is True]
    candidates = enhanced_results if require_enhanced else results

    missing: list[str] = []
    matched_index: int | None = None
    matched_steps: list[str] = []

    for result in candidates:
        sink_info = json.dumps(result.get("sinkInfo", {}), ensure_ascii=False)
        trace_steps = _trace_steps(result)
        haystack = "\n".join([sink_info, *trace_steps])
        if expected_sink not in haystack:
            continue
        absent = [needle for needle in expected_trace_contains if needle not in haystack]
        if absent:
            missing.extend(absent)
            continue
        matched_index = results.index(result)
        matched_steps = trace_steps
        break

    if matched_index is None and expected_sink:
        missing.append(f"expected_sink:{expected_sink}")
    if require_enhanced and not enhanced_results:
        missing.append("semanticBridgeEnhanced:true")

    return SarifVerification(
        ok=matched_index is not None and not missing,
        sarif=str(sarif_path),
        expected_sink=expected_sink,
        result_count=len(results),
        enhanced_result_count=len(enhanced_results),
        matched_result_index=matched_index,
        trace_steps=matched_steps,
        missing=missing,
    )


def _trace_steps(result: dict[str, Any]) -> list[str]:
    locations = result.get("codeFlows", [{}])[0].get("threadFlows", [{}])[0].get("locations", [])
    steps: list[str] = []
    for location in locations:
        physical = location.get("location", {}).get("physicalLocation", {})
        uri = physical.get("artifactLocation", {}).get("uri", "")
        region = physical.get("region", {})
        line = region.get("startLine", "?")
        affected = region.get("snippet", {}).get("affectedNodeName", "")
        text = region.get("snippet", {}).get("text", "")
        steps.append(f"{uri}:{line} {affected} {text}")
    return steps
