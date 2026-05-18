#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

python3 -m pysembridge.cli verify-chain \
  --bridge "$ROOT/bridges/cve-2025-55156-pyload/bridge.json" \
  --source "url" \
  --sink "self.c.execute.arg0"
