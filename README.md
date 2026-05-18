# PySemBridge

PySemBridge is an experimental framework for representing and compiling
Python dynamic semantic bridges for static taint analysis.

The goal is not to let an LLM directly decide whether a vulnerability exists.
Instead:

```text
LLM/code analysis proposes Semantic Bridge IR
  -> analyzer adapter compiles IR into facts/models/rules
  -> the static analyzer re-runs taint propagation
  -> complete source-to-sink traces validate the bridge
```

YASA is the primary backend for the first implementation stage. CodeQL, Pysa,
and Semgrep adapters can be added as projection backends later.

## Repository Layout

```text
pysembridge/
  ir/                 Semantic Bridge JSON schema and loader
  adapters/yasa/      YASA external facts compiler
  recognizer/         Dynamic semantic gap recognizers
  synthesizer/        LLM-assisted bridge generation components
  pipeline/           End-to-end analyzer runners
  verifier/           Trace and safe-variant validation components
bridges/              Per-CVE Semantic Bridge IR files
experiments/          Experiment scripts and generated outputs
docs/                 Design notes
```

## Quick Start

Install in editable mode:

```bash
python3 -m pip install -e .
```

Compile the included pyload bridge into YASA external facts:

```bash
pysembridge compile-yasa \
  --bridge bridges/cve-2025-55156-pyload/bridge.json \
  --output experiments/results/cve-2025-55156-pyload.yasa-facts.json
```

Without installing the console script:

```bash
python3 -m pysembridge.cli compile-yasa \
  --bridge bridges/cve-2025-55156-pyload/bridge.json \
  --output experiments/results/cve-2025-55156-pyload.yasa-facts.json
```

Equivalent script:

```bash
bash experiments/scripts/compile_pyload_yasa.sh
```

Run the current end-to-end YASA-sembridge pipeline:

```bash
python3 -m pysembridge.cli run-yasa \
  --project /home/ubuntu/llm-yasa-repair/py-bench/cve-2025-55156-pyload \
  --project-name cve-2025-55156-pyload \
  --output-dir experiments/results/tool-pipeline/cve-2025-55156-pyload \
  --yasa-dir /home/ubuntu/llm-yasa-repair/YASA-Engine-sembridge \
  --rule-config /home/ubuntu/llm-yasa-repair/py-result/tool-rules/yasa/cve-2025-55156-pyload-precise.json \
  --source url \
  --sink self.c.execute.arg0 \
  --expected-sink self.c.execute \
  --expected-trace-contains file_database.py \
  --expected-trace-contains statuses
```

The command performs:

```text
AST feature recognition
  -> semantic gap classification
  -> bridge synthesis
  -> bridge verification
  -> YASA facts compilation
  -> YASA-sembridge scan
  -> SARIF complete-trace verification
```

## Current Status

This repository currently contains:

- Tool-independent Semantic Bridge IR schema.
- AST-based semantic gap recognizer covering major Python dynamic feature families.
- Generic auto synthesis pipeline plus one executable pyload-like synthesizer.
- YASA facts compiler.
- YASA-sembridge end-to-end pipeline runner.
- Bridge and SARIF trace verifiers.

The current YASA integration uses report-level completion: YASA emits a baseline
boundary finding, then PySemBridge facts append an enhanced complete-chain SARIF
finding. Analyzer-level propagation injection is the next deeper integration
stage.

See `docs/tool-development-flow-yasa.md` for the complete PySemBridge workflow
and `integrations/yasa/yasa-sembridge-interface.patch` for the minimal YASA-side
interface patch.
