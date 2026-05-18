"""Command line entry points for PySemBridge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pysembridge.adapters.yasa.compiler import compile_bridge_to_yasa_facts
from pysembridge.ir.loader import load_bridge
from pysembridge.pipeline.yasa import run_yasa_pipeline
from pysembridge.synthesizer.auto import synthesize_auto
from pysembridge.synthesizer.pyload import synthesize_pyload_bridge
from pysembridge.verifier.chain import verify_bridge_chain
from pysembridge.verifier.sarif import verify_sarif_trace


def _compile_yasa(args: argparse.Namespace) -> None:
    bridge = load_bridge(Path(args.bridge))
    facts = compile_bridge_to_yasa_facts(bridge)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(facts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _verify_chain(args: argparse.Namespace) -> None:
    bridge = load_bridge(Path(args.bridge))
    result = verify_bridge_chain(bridge, args.source, args.sink)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    if not result.ok:
        raise SystemExit(1)


def _synthesize(args: argparse.Namespace) -> None:
    if args.template != "pyload":
        raise SystemExit(f"Unsupported synthesis template: {args.template}")
    bridge = synthesize_pyload_bridge(Path(args.project), args.project_name)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bridge, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _synthesize_auto(args: argparse.Namespace) -> None:
    result = synthesize_auto(Path(args.project), args.project_name)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "bundle":
        output.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return

    if not result.bridges:
        raise SystemExit("No executable bridge was synthesized. Use --format bundle to inspect candidate gap specs.")
    output.write_text(json.dumps(result.bridges[0], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _verify_sarif(args: argparse.Namespace) -> None:
    result = verify_sarif_trace(
        Path(args.sarif),
        expected_sink=args.expected_sink,
        expected_trace_contains=args.expected_trace_contains or [],
        require_enhanced=not args.allow_baseline,
    )
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    if not result.ok:
        raise SystemExit(1)


def _run_yasa(args: argparse.Namespace) -> None:
    result = run_yasa_pipeline(
        project_path=Path(args.project),
        project_name=args.project_name,
        output_dir=Path(args.output_dir),
        yasa_dir=Path(args.yasa_dir),
        rule_config=Path(args.rule_config),
        source_expr=args.source,
        sink_expr=args.sink,
        expected_sink=args.expected_sink,
        expected_trace_contains=args.expected_trace_contains or [],
        checker_id=args.checker_id,
    )
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    if not result.ok:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pysembridge",
        description="Compile tool-independent Semantic Bridge IR into analyzer-specific facts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_yasa = subparsers.add_parser(
        "compile-yasa",
        help="Compile a Semantic Bridge JSON file into YASA external facts.",
    )
    compile_yasa.add_argument("--bridge", required=True, help="Path to a Semantic Bridge JSON file.")
    compile_yasa.add_argument("--output", required=True, help="Path to write YASA facts JSON.")
    compile_yasa.set_defaults(func=_compile_yasa)

    verify_chain = subparsers.add_parser(
        "verify-chain",
        help="Verify that a Semantic Bridge IR connects a source expression to a sink expression.",
    )
    verify_chain.add_argument("--bridge", required=True, help="Path to a Semantic Bridge JSON file.")
    verify_chain.add_argument("--source", required=True, help="Source expression in flow facts.")
    verify_chain.add_argument("--sink", required=True, help="Sink expression in flow facts.")
    verify_chain.set_defaults(func=_verify_chain)

    synthesize = subparsers.add_parser(
        "synthesize",
        help="Synthesize a Semantic Bridge IR from a Python CVE benchmark project.",
    )
    synthesize.add_argument("--project", required=True, help="Path to the CVE project source tree.")
    synthesize.add_argument("--output", required=True, help="Path to write synthesized bridge JSON.")
    synthesize.add_argument("--project-name", help="Project name stored in bridge JSON.")
    synthesize.add_argument(
        "--template",
        default="pyload",
        choices=["pyload"],
        help="Synthesis template/pattern family to use.",
    )
    synthesize.set_defaults(func=_synthesize)

    synthesize_auto_parser = subparsers.add_parser(
        "synthesize-auto",
        help="Run the generic feature extractor/classifier and synthesize bridge candidates.",
    )
    synthesize_auto_parser.add_argument("--project", required=True, help="Path to the CVE project source tree.")
    synthesize_auto_parser.add_argument("--output", required=True, help="Path to write bridge JSON or bundle JSON.")
    synthesize_auto_parser.add_argument("--project-name", help="Project name stored in generated output.")
    synthesize_auto_parser.add_argument(
        "--format",
        default="bridge",
        choices=["bridge", "bundle"],
        help="Output the first executable bridge or the full classification/spec bundle.",
    )
    synthesize_auto_parser.set_defaults(func=_synthesize_auto)

    verify_sarif = subparsers.add_parser(
        "verify-sarif",
        help="Verify that a SARIF report contains a complete enhanced source-to-sink trace.",
    )
    verify_sarif.add_argument("--sarif", required=True, help="Path to report.sarif.")
    verify_sarif.add_argument("--expected-sink", required=True, help="Expected sink text, for example self.c.execute.")
    verify_sarif.add_argument(
        "--expected-trace-contains",
        action="append",
        help="Trace text that must appear in the matched result. Can be passed multiple times.",
    )
    verify_sarif.add_argument(
        "--allow-baseline",
        action="store_true",
        help="Allow matching non-semanticBridgeEnhanced results.",
    )
    verify_sarif.set_defaults(func=_verify_sarif)

    run_yasa = subparsers.add_parser(
        "run-yasa",
        help="Run end-to-end PySemBridge synthesis, YASA-sembridge scan, and trace verification.",
    )
    run_yasa.add_argument("--project", required=True, help="Path to the CVE project source tree.")
    run_yasa.add_argument("--project-name", required=True, help="Project/CVE name for output artifact names.")
    run_yasa.add_argument("--output-dir", required=True, help="Directory for generated bridge/facts/report/summary.")
    run_yasa.add_argument("--yasa-dir", required=True, help="Path to YASA-Engine-sembridge.")
    run_yasa.add_argument("--rule-config", required=True, help="YASA rule config JSON.")
    run_yasa.add_argument("--source", required=True, help="Bridge verifier source expression.")
    run_yasa.add_argument("--sink", required=True, help="Bridge verifier sink expression.")
    run_yasa.add_argument("--expected-sink", required=True, help="Expected sink text in final SARIF.")
    run_yasa.add_argument(
        "--expected-trace-contains",
        action="append",
        help="Trace text that must appear in the enhanced SARIF result. Can be passed multiple times.",
    )
    run_yasa.add_argument(
        "--checker-id",
        default="taint_flow_python_input_inner",
        help="YASA checker id to run.",
    )
    run_yasa.set_defaults(func=_run_yasa)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
