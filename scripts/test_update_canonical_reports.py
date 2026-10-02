"""Regression tests for canonical benchmark-run selection."""

import json
import unittest
from types import SimpleNamespace

from update_canonical_reports import select_canonical_run


class CanonicalRunSelectionTests(unittest.TestCase):
    class Run:
        def __init__(self, name: str, reader_ids: list[str], mtime: int):
            self.name = name
            self.data = {"measurements": [{"reader_id": reader_id} for reader_id in reader_ids]}
            self.mtime = mtime

        def read_text(self, encoding: str) -> str:
            return json.dumps(self.data)

        def stat(self):
            return SimpleNamespace(st_mtime=self.mtime)

    def test_new_complete_matrix_beats_older_legacy_breadth(self):
        old = self.Run("old.json", ["a", "b", "legacy"] * 100, 1)
        fresh = self.Run("fresh.json", ["a", "b"], 2)
        self.assertEqual(select_canonical_run([old, fresh], {"a", "b"}), fresh)

    def test_newer_selective_probe_does_not_replace_complete_matrix(self):
        complete = self.Run("complete.json", ["a", "b"], 1)
        probe = self.Run("probe.json", ["a"], 2)
        self.assertEqual(select_canonical_run([complete, probe], {"a", "b"}), complete)


if __name__ == "__main__":
    unittest.main()
