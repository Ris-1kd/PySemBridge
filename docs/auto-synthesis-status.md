# Automatic Bridge Synthesis Status

## Current Capability

PySemBridge now has two automatic synthesis layers:

```text
1. generic recognizer/classifier for six major Python semantic-gap families
2. concrete executable bridge synthesis for the pyload-like
   receiver + container + string_builder family
```

Supported dynamic semantic gap family:

```text
receiver resolution
  + container/tuple element propagation
  + generator/join string construction
  + f-string argument to SQL sink
```

This corresponds to the pyload CVE pattern:

```text
url
  -> data[*][3]
  -> x[3] for x in data
  -> statuses = "','".join(...)
  -> self.c.execute(...)
```

## Implemented Commands

Run the generic classifier/synthesizer and output a full bundle:

```bash
bash experiments/scripts/synthesize_auto_pyload_bundle.sh
```

Run the generic auto pipeline end to end:

```bash
bash experiments/scripts/run_auto_generic_pyload_sembridge.sh
```

Generate bridge JSON automatically from the CVE source tree:

```bash
bash experiments/scripts/synthesize_pyload_bridge.sh
```

Run the full automatic pipeline:

```bash
bash experiments/scripts/run_auto_pyload_sembridge.sh
```

The full pipeline performs:

```text
CVE source project
  -> AST/template recognizer
  -> generated bridge.json
  -> bridge verifier
  -> YASA facts compiler
  -> YASA-sembridge scan
  -> enhanced complete-chain SARIF
```

## Generated Artifacts

```text
experiments/results/generated/cve-2025-55156-pyload.auto-bundle.json
experiments/results/generated/cve-2025-55156-pyload.auto.bridge.json
experiments/results/generated/cve-2025-55156-pyload.auto.yasa-facts.json
experiments/results/yasa-sembridge-generic-auto/cve-2025-55156-pyload/report.sarif
experiments/results/generated/cve-2025-55156-pyload.bridge.json
experiments/results/generated/cve-2025-55156-pyload.yasa-facts.json
experiments/results/yasa-sembridge-auto/cve-2025-55156-pyload/report.sarif
experiments/results/yasa-sembridge-auto/cve-2025-55156-pyload/semantic_bridge_summary.json
```

## Verified Result

The automatic run produced two SARIF findings:

```text
0. YASA baseline boundary finding
   sink: db.update_link_info

1. PySemBridge enhanced complete-chain finding
   semanticBridgeEnhanced: true
   sink: self.c.execute(...)
```

Enhanced trace:

```text
poc_cve_2025_55156_pyload.py:16 cve_2025_55156_source()
poc_cve_2025_55156_pyload.py:16 url
poc_cve_2025_55156_pyload.py:17 data
poc_cve_2025_55156_pyload.py:18 db.update_link_info
file_database.py:261 FileDatabaseMethods.update_link_info
file_database.py:270 statuses
file_database.py:271 self.c.execute
```

## Implementation Files

PySemBridge:

```text
pysembridge/synthesizer/pyload.py
pysembridge/verifier/chain.py
pysembridge/cli.py
experiments/scripts/synthesize_pyload_bridge.sh
experiments/scripts/run_auto_pyload_sembridge.sh
```

YASA-sembridge:

```text
YASA-Engine-sembridge/src/engine/analyzer/common/semantic-bridge-facts-loader.ts
YASA-Engine-sembridge/src/engine/analyzer/common/semantic-bridge-report-augmenter.ts
YASA-Engine-sembridge/src/interface/starter.ts
YASA-Engine-sembridge/src/config.ts
```

## Boundary

This is not yet a fully universal automatic semantic bridge engine.

Currently implemented:

```text
generic six-family AST feature classification
generic candidate gap spec generation
pyload-like receiver/container/string_builder executable bridge generation
```

Not yet implemented:

```text
executable bridge synthesis for every family
precise family ranking using baseline traces
LLM-assisted evidence extraction for ambiguous patterns
tool-specific projections beyond YASA facts/report enhancement
```

The design now has the right extension points:

```text
recognizer/      identify dynamic feature patterns
synthesizer/     emit bridge facts
verifier/        check source-to-sink bridge closure
adapters/        project bridge facts to YASA/CodeQL/Pysa/Semgrep
```

Next step: add one synthesizer per dynamic feature family and make the top-level
`synthesize` command dispatch among them.
