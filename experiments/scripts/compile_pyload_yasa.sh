#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 -m pysembridge.cli compile-yasa \
  --bridge "$ROOT/bridges/cve-2025-55156-pyload/bridge.json" \
  --output "$ROOT/experiments/results/cve-2025-55156-pyload.yasa-facts.json"
