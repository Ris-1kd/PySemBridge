from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from pysembridge.ir.loader import load_bridge


class BridgeLoaderValidationTest(unittest.TestCase):
    def test_loads_minimal_valid_bridge(self) -> None:
        bridge = self._load(
            {
                "version": "0.1",
                "bridge_id": "minimal",
                "language": "python",
                "project": "demo",
                "gap_types": ["receiver"],
            }
        )

        self.assertEqual(bridge["bridge_id"], "minimal")
        self.assertEqual(bridge["language"], "python")

    def test_rejects_missing_required_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "project"):
            self._load(
                {
                    "version": "0.1",
                    "bridge_id": "missing-project",
                    "language": "python",
                    "gap_types": ["receiver"],
                }
            )

    def test_rejects_non_python_language(self) -> None:
        with self.assertRaisesRegex(ValueError, "language"):
            self._load(
                {
                    "version": "0.1",
                    "bridge_id": "bad-language",
                    "language": "javascript",
                    "project": "demo",
                    "gap_types": ["receiver"],
                }
            )

    def test_rejects_empty_gap_types(self) -> None:
        with self.assertRaisesRegex(ValueError, "gap_types"):
            self._load(
                {
                    "version": "0.1",
                    "bridge_id": "empty-gaps",
                    "language": "python",
                    "project": "demo",
                    "gap_types": [],
                }
            )

    def _load(self, bridge: dict[str, object]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bridge.json"
            path.write_text(json.dumps(bridge), encoding="utf-8")
            return load_bridge(path)


if __name__ == "__main__":
    unittest.main()
