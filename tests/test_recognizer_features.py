from pathlib import Path
import unittest

from pysembridge.recognizer.features import extract_python_features


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "recognizer_gaps"


class RecognizerFeatureExtractionTest(unittest.TestCase):
    def test_extracts_dynamic_gap_features_from_small_sample(self) -> None:
        hits = extract_python_features(FIXTURE_DIR)
        by_kind = {}
        for hit in hits:
            by_kind.setdefault(hit.kind, []).append(hit)

        expected_kinds = {
            "dynamic_attribute_access",
            "dict_literal",
            "callback_dict",
            "container_subscript",
            "percent_string_format_builder",
            "string_format_builder",
            "f_string_builder",
            "higher_order_function",
            "callback_argument",
        }

        self.assertTrue(
            expected_kinds.issubset(by_kind),
            f"missing feature kinds: {sorted(expected_kinds.difference(by_kind))}",
        )

        self.assertTrue(
            any(hit.expr == "getattr(handler, handler_name)" for hit in by_kind["dynamic_attribute_access"])
        )
        self.assertTrue(any(hit.expr == 'callbacks["audit"]' for hit in by_kind["container_subscript"]))
        self.assertTrue(any(hit.expr == '"payload=%s" % payload' for hit in by_kind["percent_string_format_builder"]))
        self.assertTrue(any(hit.expr == '"payload {}".format(payload)' for hit in by_kind["string_format_builder"]))
        self.assertTrue(any(hit.expr == "f\"{message}:{second_result}\"" for hit in by_kind["f_string_builder"]))
        self.assertTrue(any(hit.expr == "map(audit, [payload])" for hit in by_kind["higher_order_function"]))


if __name__ == "__main__":
    unittest.main()
