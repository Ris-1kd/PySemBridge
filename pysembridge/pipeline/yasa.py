"""End-to-end YASA-sembridge pipeline runner."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pysembridge.adapters.yasa.compiler import compile_bridge_to_yasa_facts
from pysembridge.synthesizer.auto import synthesize_auto
from pysembridge.verifier.chain import verify_bridge_chain
from pysembridge.verifier.sarif import verify_sarif_trace


@dataclass(frozen=True)
class YasaPipelineResult:
    ok: bool
    project: str
    bridge_path: str
    facts_path: str
    report_dir: str
    sarif_path: str
    summary_path: str
    bundle_path: str
    bridge_verification: dict[str, Any]
    sarif_verification: dict[str, Any]
    yasa_returncode: int
    yasa_stdout_path: str
    yasa_stderr_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "project": self.project,
            "bridge_path": self.bridge_path,
            "facts_path": self.facts_path,
            "report_dir": self.report_dir,
            "sarif_path": self.sarif_path,
            "summary_path": self.summary_path,
            "bundle_path": self.bundle_path,
            "bridge_verification": self.bridge_verification,
            "sarif_verification": self.sarif_verification,
            "yasa_returncode": self.yasa_returncode,
            "yasa_stdout_path": self.yasa_stdout_path,
            "yasa_stderr_path": self.yasa_stderr_path,
        }


def run_yasa_pipeline(
    project_path: Path,
    project_name: str,
    output_dir: Path,
    yasa_dir: Path,
    rule_config: Path,
    source_expr: str,
    sink_expr: str,
    expected_sink: str,
    expected_trace_contains: list[str] | None = None,
    checker_id: str = "taint_flow_python_input_inner",
) -> YasaPipelineResult:
    project_path = project_path.resolve()
    output_dir = output_dir.resolve()
    yasa_dir = yasa_dir.resolve()
    rule_config = rule_config.resolve()
    generated_dir = output_dir / "generated"
    report_dir = output_dir / "yasa"
    generated_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    bundle_path = generated_dir / f"{project_name}.auto-bundle.json"
    bridge_path = generated_dir / f"{project_name}.bridge.json"
    facts_path = generated_dir / f"{project_name}.yasa-facts.json"
    stdout_path = report_dir / "yasa.stdout.log"
    stderr_path = report_dir / "yasa.stderr.log"
    summary_path = output_dir / "pipeline-summary.json"

    auto_result = synthesize_auto(project_path, project_name)
    bundle_path.write_text(json.dumps(auto_result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not auto_result.bridges:
        result = YasaPipelineResult(
            ok=False,
            project=project_name,
            bridge_path="",
            facts_path="",
            report_dir=str(report_dir),
            sarif_path=str(report_dir / "report.sarif"),
            summary_path=str(summary_path),
            bundle_path=str(bundle_path),
            bridge_verification={"ok": False, "missing": ["executable_bridge"]},
            sarif_verification={"ok": False, "missing": ["not_run"]},
            yasa_returncode=-1,
            yasa_stdout_path=str(stdout_path),
            yasa_stderr_path=str(stderr_path),
        )
        _write_summary(summary_path, result)
        return result

    bridge = auto_result.bridges[0]
    bridge_path.write_text(json.dumps(bridge, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    bridge_verification = verify_bridge_chain(bridge, source_expr, sink_expr)
    facts = compile_bridge_to_yasa_facts(bridge)
    facts_path.write_text(json.dumps(facts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    cmd = [
        "npx",
        "tsx",
        "src/main.ts",
        "--sourcePath",
        str(project_path),
        "--language",
        "python",
        "--report",
        str(report_dir),
        "--ruleConfigFile",
        str(rule_config),
        "--semanticBridgeFacts",
        str(facts_path),
        "--checkerIds",
        checker_id,
        "--entrypointMode",
        "ONLY_CUSTOM",
        "--workerCount",
        "1",
        "--incremental",
        "false",
        "--taintTraceOutputStrategy",
        "full",
        "--uastSDKPath",
        str(yasa_dir / "uast4py-linux-amd64"),
    ]
    process = subprocess.run(cmd, cwd=yasa_dir, text=True, capture_output=True, check=False)
    stdout_path.write_text(process.stdout, encoding="utf-8")
    stderr_path.write_text(process.stderr, encoding="utf-8")

    sarif_path = report_dir / "report.sarif"
    if sarif_path.exists():
        sarif_verification = verify_sarif_trace(
            sarif_path,
            expected_sink=expected_sink,
            expected_trace_contains=expected_trace_contains,
            require_enhanced=True,
        )
        sarif_dict = sarif_verification.to_dict()
    else:
        sarif_dict = {"ok": False, "missing": ["report.sarif"], "sarif": str(sarif_path)}

    result = YasaPipelineResult(
        ok=bridge_verification.ok and sarif_dict.get("ok") is True and process.returncode == 0,
        project=project_name,
        bridge_path=str(bridge_path),
        facts_path=str(facts_path),
        report_dir=str(report_dir),
        sarif_path=str(sarif_path),
        summary_path=str(summary_path),
        bundle_path=str(bundle_path),
        bridge_verification=bridge_verification.to_dict(),
        sarif_verification=sarif_dict,
        yasa_returncode=process.returncode,
        yasa_stdout_path=str(stdout_path),
        yasa_stderr_path=str(stderr_path),
    )
    _write_summary(summary_path, result)
    return result


def _write_summary(path: Path, result: YasaPipelineResult) -> None:
    path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
