# PySemBridge Tool Flow with YASA

This document describes the intended development and execution flow for PySemBridge, using YASA semantic supplementation as the concrete backend.

## Repository Boundary

PySemBridge is the umbrella repository for the bridge framework and the
reproducible YASA integration. It contains:

- Semantic Bridge IR schema and bridge examples.
- Recognizers, synthesizers, compilers, verifiers, and pipeline orchestration code.
- The full YASA-sembridge engine copy used by the current experiments.
- Documentation and scripts needed to reproduce the workflow.

It should not contain `yasa-llm-taint-repair`, benchmark source trees, generated
analyzer outputs, `node_modules`, or runtime logs. The integrated YASA tool is
kept in:

```text
integrations/yasa/YASA-Engine-sembridge/
```

This directory is the canonical backend to use for `--semanticBridgeFacts`
experiments.

## Core Idea

PySemBridge does not replace a static analyzer. It describes missing Python dynamic semantics in a tool-independent IR, then projects the IR into analyzer-specific facts or models.

```text
Python project
  -> feature recognition
  -> semantic gap classification
  -> Semantic Bridge IR synthesis
  -> bridge verification
  -> YASA facts compilation
  -> YASA-sembridge run
  -> SARIF/report verification
```

For YASA, the current integration is report-level semantic supplementation: PySemBridge compiles bridge evidence into `yasa_injection` facts, YASA loads those facts through `--semanticBridgeFacts`, and the SARIF report is augmented with a complete-chain finding from the original boundary finding to the real sink.

## Functional Components

`pysembridge/ir`

Defines the JSON schema and loader for Semantic Bridge IR. This is the stable contract between recognition/synthesis and analyzer adapters.

`pysembridge/recognizer`

Extracts Python AST features that often cause under-tainting, such as dynamic dispatch, container/key propagation, comprehensions/generators, formatting, callback-like calls, and wrapper boundaries.

`pysembridge/synthesizer`

Builds bridge candidates from recognized features. It contains both case-oriented synthesis and a generic auto synthesis path that emits either a bridge or a full classification bundle.

`pysembridge/adapters/yasa`

Compiles Semantic Bridge IR into YASA-facing external facts. The output contains `graph_facts`, `flow_facts`, validation metadata, and evidence locations.

`pysembridge/verifier`

Checks whether a bridge connects the intended source expression to the intended sink expression, and whether the final SARIF contains an enhanced complete trace.

`pysembridge/pipeline`

Runs the end-to-end YASA workflow: synthesize bridge, compile facts, run YASA, augment/read reports, and write summaries.

## YASA-sembridge Integrated Tool

The integrated YASA copy adds a narrow interface:

- `Config.semanticBridgeFactsFile`
- `Config.semanticBridgeFacts`
- CLI option `--semanticBridgeFacts <file>`
- facts loading before analyzer construction
- SARIF augmentation after normal analyzer output

The integration adds two helper files in YASA:

```text
src/engine/analyzer/common/semantic-bridge-facts-loader.ts
src/engine/analyzer/common/semantic-bridge-report-augmenter.ts
```

The loader validates and stores facts. The augmenter appends a `semanticBridgeEnhanced` SARIF result and writes `semantic_bridge_summary.json`.

## Development Workflow

1. Identify an under-tainting case.

Run baseline YASA with a precise source/sink rule and confirm whether the tool stops at a boundary sink, misses a dynamic call edge, or loses container/string semantics.

2. Inspect the Python code.

Find the semantic gap. Examples:

- Source value is stored inside a list/dict and later unpacked.
- A boundary function delegates to a real sink through a method call.
- Query/string construction hides the source from the analyzer.
- Dynamic dispatch or framework wrapper hides the real entry.

3. Generate or write Semantic Bridge IR.

Use either a checked-in bridge:

```bash
python3 -m pysembridge.cli verify-chain \
  --bridge bridges/cve-2025-55156-pyload/bridge.json \
  --source url \
  --sink self.c.execute.arg0
```

Or synthesize one:

```bash
python3 -m pysembridge.cli synthesize-auto \
  --project /path/to/python/project \
  --project-name cve-name \
  --output experiments/results/generated/cve-name.auto-bundle.json \
  --format bundle
```

4. Compile bridge facts for YASA.

```bash
python3 -m pysembridge.cli compile-yasa \
  --bridge bridges/cve-2025-55156-pyload/bridge.json \
  --output experiments/results/cve-2025-55156-pyload.yasa-facts.json
```

5. Run YASA-sembridge.

YASA still receives the normal rule config. PySemBridge facts are passed separately:

```bash
npx tsx src/main.ts \
  --sourcePath /path/to/python/project \
  --language python \
  --report experiments/results/yasa-sembridge/cve-name \
  --ruleConfigFile /path/to/precise-yasa-rule.json \
  --semanticBridgeFacts experiments/results/cve-name.yasa-facts.json \
  --checkerIds taint_flow_python_input_inner \
  --entrypointMode ONLY_CUSTOM
```

6. Verify the enhanced report.

```bash
python3 -m pysembridge.cli verify-sarif \
  --sarif experiments/results/yasa-sembridge/cve-name/report.sarif \
  --expected-sink self.c.execute \
  --expected-trace-contains file_database.py
```

7. Record the result.

Keep generated reports under `experiments/results/`, which is intentionally
ignored by git. Commit stable bridge IR, PySemBridge source code, experiment
scripts, docs, and the integrated YASA-sembridge source tree.

## pyload Example

The pyload case demonstrates a boundary-to-real-sink bridge:

```text
url
  -> data[*][3]
  -> generator.element
  -> statuses
  -> self.c.execute.arg0
```

Baseline YASA can report a boundary around `db.update_link_info(data)`, but the real SQL sink is inside `FileDatabaseMethods.update_link_info`. PySemBridge records the missing call edge and container/string propagation as Semantic Bridge IR, compiles it to YASA facts, and lets YASA-sembridge include an enhanced complete-chain finding in the report.

## Why Keep a Full YASA-sembridge Copy

The current repository keeps a full modified YASA copy because:

- The experiment can be reproduced from a single repository checkout.
- The exact backend source used for SARIF augmentation is visible.
- The older standalone diff/patch file is no longer needed.
- Generated dependency and runtime directories can still stay out of git.

If the interface stabilizes further, the next step is to upstream the changes or
maintain a dedicated YASA fork/branch. This repository copy remains the
reproducible experimental backend.
