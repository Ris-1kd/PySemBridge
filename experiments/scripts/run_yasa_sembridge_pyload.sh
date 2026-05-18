#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKSPACE="$(cd "$ROOT/.." && pwd)"

bash "$ROOT/experiments/scripts/compile_pyload_yasa.sh"

cd "$WORKSPACE/YASA-Engine-sembridge"

npx tsx src/main.ts \
  --sourcePath "$WORKSPACE/py-bench/cve-2025-55156-pyload" \
  --language python \
  --report "$ROOT/experiments/results/yasa-sembridge/cve-2025-55156-pyload" \
  --ruleConfigFile "$WORKSPACE/py-result/tool-rules/yasa/cve-2025-55156-pyload-precise.json" \
  --semanticBridgeFacts "$ROOT/experiments/results/cve-2025-55156-pyload.yasa-facts.json" \
  --checkerIds taint_flow_python_input_inner \
  --entrypointMode ONLY_CUSTOM \
  --workerCount 1 \
  --incremental false \
  --taintTraceOutputStrategy full \
  --uastSDKPath "$WORKSPACE/YASA-Engine-sembridge/uast4py-linux-amd64"
