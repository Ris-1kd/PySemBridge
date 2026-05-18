#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKSPACE="$(cd "$ROOT/.." && pwd)"
BRIDGE="$ROOT/experiments/results/generated/cve-2025-55156-pyload.bridge.json"
FACTS="$ROOT/experiments/results/generated/cve-2025-55156-pyload.yasa-facts.json"
REPORT="$ROOT/experiments/results/yasa-sembridge-auto/cve-2025-55156-pyload"

bash "$ROOT/experiments/scripts/synthesize_pyload_bridge.sh"

python3 -m pysembridge.cli verify-chain \
  --bridge "$BRIDGE" \
  --source "url" \
  --sink "self.c.execute.arg0"

python3 -m pysembridge.cli compile-yasa \
  --bridge "$BRIDGE" \
  --output "$FACTS"

cd "$WORKSPACE/YASA-Engine-sembridge"

npx tsx src/main.ts \
  --sourcePath "$WORKSPACE/py-bench/cve-2025-55156-pyload" \
  --language python \
  --report "$REPORT" \
  --ruleConfigFile "$WORKSPACE/py-result/tool-rules/yasa/cve-2025-55156-pyload-precise.json" \
  --semanticBridgeFacts "$FACTS" \
  --checkerIds taint_flow_python_input_inner \
  --entrypointMode ONLY_CUSTOM \
  --workerCount 1 \
  --incremental false \
  --taintTraceOutputStrategy full \
  --uastSDKPath "$WORKSPACE/YASA-Engine-sembridge/uast4py-linux-amd64"
