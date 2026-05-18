# End-to-End Tool Flow

## Goal

`pysembridge run-yasa` is the current single-command workflow for the research
prototype. It turns a CVE source project into a verified complete taint trace
using the YASA-sembridge backend.

## Command

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

## Pipeline

```text
1. AST/source feature extraction
2. semantic gap classification
3. executable bridge synthesis when a concrete synthesizer matches
4. bridge internal reachability verification
5. YASA facts compilation
6. YASA-sembridge scan with --semanticBridgeFacts
7. SARIF enhanced-trace verification
8. pipeline-summary.json output
```

## Verified Pyload Result

The current pyload run finished with:

```json
{
  "ok": true,
  "yasa_returncode": 0,
  "bridge_verification": {
    "ok": true
  },
  "sarif_verification": {
    "ok": true,
    "result_count": 2,
    "enhanced_result_count": 1,
    "matched_result_index": 1
  }
}
```

Enhanced trace:

```text
cve_2025_55156_source()
url
data
db.update_link_info
FileDatabaseMethods.update_link_info
statuses
self.c.execute
```

## Output Artifacts

```text
experiments/results/tool-pipeline/cve-2025-55156-pyload/
  pipeline-summary.json
  generated/
    cve-2025-55156-pyload.auto-bundle.json
    cve-2025-55156-pyload.bridge.json
    cve-2025-55156-pyload.yasa-facts.json
  yasa/
    report.sarif
    semantic_bridge_summary.json
    scan_summary.json
    yasa.stdout.log
    yasa.stderr.log
```

## Current Integration Boundary

The current YASA integration is a report-level completion backend:

```text
YASA baseline boundary finding
  + Semantic Bridge facts
  -> enhanced complete-chain SARIF finding
```

It is not yet analyzer-native propagation:

```text
YASA symbolic execution
  -> internally consumes call_edges/flow_facts
  -> native complete finding
```

The report-level backend is useful for validating whether generated bridge facts
are sufficient to recover the missing source-to-sink chain. Analyzer-level
injection is the next implementation milestone.
