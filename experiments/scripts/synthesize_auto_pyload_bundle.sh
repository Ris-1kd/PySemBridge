#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKSPACE="$(cd "$ROOT/.." && pwd)"

python3 -m pysembridge.cli synthesize-auto \
  --project "$WORKSPACE/py-bench/cve-2025-55156-pyload" \
  --project-name "cve-2025-55156-pyload" \
  --format bundle \
  --output "$ROOT/experiments/results/generated/cve-2025-55156-pyload.auto-bundle.json"
