"""Check Markdown rankings, timing gaps, missing cases and fixture verification."""
import hashlib
import unittest
from bootstrap_benchmark_corpus import verify
from update_readme_benchmarks import render


class ReadmeBenchmarkTests(unittest.TestCase):
    def test_rank_score_and_timing_gaps_use_comparable_cases(self):
        data = {
            "raw_file": "example.json",
            "readers": [{"name": name} for name in ["BlazePDF", "Reference", "Unmeasured"]],
            "measurements": [
                {"reader": "BlazePDF", "work": "classify", "document": "A", "status": "ok", "median_ms": 10},
                {"reader": "Reference", "work": "classify", "document": "A", "status": "ok", "median_ms": 5},
                {"reader": "BlazePDF", "work": "classify", "document": "B", "status": "ok", "median_ms": 2},
                {"reader": "Reference", "work": "classify", "document": "B", "status": "ok", "median_ms": 4},
                {"reader": "Unmeasured", "work": "classify", "document": "A", "status": "failed"},
            ],
        }
        summary, full = render(data)
        self.assertIn("| BlazePDF | 1 | 1 | 0 | 0 | 2 / 2 | 1.50 |", summary)
        self.assertIn("| A | 10.000 | Reference | 5.000 | -5.000 | 0.50× |", summary)
        self.assertIn("| B | 2.000 | Reference | 4.000 | +2.000 | 2.00× |", summary)
        self.assertIn("Catalogued but not measured/scored: Unmeasured", summary)
        self.assertIn("| A | 10.000 | 5.000 |", full)

    def test_missing_reference_is_not_zero_and_duplicate_adapters_share_one_product(self):
        data = {"raw_file": "example.json", "readers": [{"name": "BlazePDF"}],
                "measurements": [
                    {"reader": "one", "product": "BlazePDF", "work": "open", "document": "Only", "status": "ok", "median_ms": 3},
                    {"reader": "two", "product": "BlazePDF", "work": "open", "document": "Only", "status": "ok", "median_ms": 9},
                ]}
        summary, _ = render(data)
        self.assertIn("| BlazePDF | 1 | 0 | 0 | 0 | 1 / 1 | 1.00 |", summary)
        self.assertIn("| Only | 3.000 | — | — | — | — |", summary)

    def test_fixture_hash_mismatch_is_rejected(self):
        content = b"fixture"
        self.assertEqual(verify(content, hashlib.sha256(content).hexdigest()), content)
        with self.assertRaises(ValueError):
            verify(content, "0" * 64)


if __name__ == "__main__":
    unittest.main()
