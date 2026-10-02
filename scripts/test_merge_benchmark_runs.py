"""Regression check for run merging: rows swap in, provenance stays honest."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

from merge_benchmark_runs import merge


BASE_STAMP = "2026-01-01T00:00:00+00:00"
SUPPLEMENT_STAMP = "2026-06-30T12:00:00+00:00"


def row(product: str, work: str, document: str, ms: float, status: str = "ok") -> dict:
    return {
        "product": product,
        "reader": product,
        "work": work,
        "document": document,
        "status": status,
        "samples_ms": [ms],
    }


def write(directory: Path, name: str, payload: dict) -> Path:
    path = directory / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def main() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        base = write(
            directory,
            "benchmark-base.json",
            {
                "generated_at": BASE_STAMP,
                "raw_file": "benchmark-base.json",
                "readers": [{"name": "BlazePDF", "product": "BlazePDF", "work": "classify only"}],
                "measurements": [
                    row("BlazePDF", "classify only", "Text-heavy", 30.0),
                    row("MuPDF", "classify only", "Text-heavy", 9.0),
                ],
            },
        )
        supplement = write(
            directory,
            "benchmark-probe.json",
            {
                "generated_at": SUPPLEMENT_STAMP,
                "readers": [{"name": "BlazePDF", "product": "BlazePDF", "work": "classify only"}],
                "measurements": [
                    row("BlazePDF", "classify only", "Text-heavy", 11.0),
                    # A failed row must never displace a good base measurement.
                    row("MuPDF", "classify only", "Text-heavy", 0.0, status="failed"),
                ],
            },
        )

        merged = merge(base, [supplement], "benchmark-merged-test.json")

        rows = {(m["product"], m["work"], m["document"]): m for m in merged["measurements"]}
        assert len(rows) == 2, f"row count changed: {len(rows)}"
        assert rows[("BlazePDF", "classify only", "Text-heavy")]["samples_ms"] == [11.0], (
            "supplement did not replace the base measurement"
        )
        assert rows[("MuPDF", "classify only", "Text-heavy")]["samples_ms"] == [9.0], (
            "a failed supplemental row displaced a good base measurement"
        )

        # Provenance: the artifact is dated when it was assembled, not when the
        # base run was measured, and it names every source with its share.
        assert merged["generated_at"] != BASE_STAMP, "merged run inherited the base timestamp"
        datetime.fromisoformat(merged["generated_at"])
        assert merged["raw_file"] == "benchmark-merged-test.json", (
            f"raw_file should name the merged artifact, got {merged['raw_file']}"
        )

        sources = {source["file"]: source for source in merged["merged_from"]}
        assert set(sources) == {"benchmark-base.json", "benchmark-probe.json"}
        assert sources["benchmark-base.json"]["role"] == "base"
        assert sources["benchmark-base.json"]["generated_at"] == BASE_STAMP
        assert sources["benchmark-base.json"]["measurements_used"] == 1, (
            "the base should still own the row no supplement replaced"
        )
        assert sources["benchmark-probe.json"]["role"] == "supplement"
        assert sources["benchmark-probe.json"]["generated_at"] == SUPPLEMENT_STAMP
        assert sources["benchmark-probe.json"]["measurements_used"] == 1, (
            "the supplement should own exactly the row it replaced"
        )
        assert sum(s["measurements_used"] for s in merged["merged_from"]) == len(rows), (
            "contributed counts must account for every merged row"
        )

        # Without an output name the artifact still names a real file.
        assert merge(base, [supplement])["raw_file"] == "benchmark-base.json"

    print("merge_benchmark_runs: rows swap in, failed rows ignored, provenance recorded")


if __name__ == "__main__":
    main()
