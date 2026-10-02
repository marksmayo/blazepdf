"""Publish the latest reproducible run as the two stable benchmark report URLs."""

from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
EXCLUDED_PRODUCTS = {
    "UPDF",
    "Slim PDF Reader",
    "sioyek",
    "PDF-XChange Editor",
    "WPS Office PDF",
    "Nitro PDF Pro",
    "Soda PDF Desktop",
    "PDFgear",
    "Microsoft Edge PDF reader",
}


def active_reader_ids() -> set[str]:
    readers = json.loads((ROOT / "benchmarks" / "readers.json").read_text(encoding="utf-8"))["readers"]
    return {
        reader["id"]
        for reader in readers
        if reader.get("product", reader["name"]) not in EXCLUDED_PRODUCTS
    }


def select_canonical_run(runs: list[Path], active_ids: set[str]) -> Path:
    """Prefer the newest full active-matrix run over stale legacy breadth."""
    scored = []
    for candidate in runs:
        try:
            candidate_data = json.loads(candidate.read_text(encoding="utf-8"))
            measured_ids = {
                row.get("reader_id") for row in candidate_data.get("measurements", [])
            }
            coverage = len(measured_ids & active_ids)
            score = (coverage == len(active_ids), coverage, candidate.stat().st_mtime)
        except (OSError, json.JSONDecodeError):
            continue
        scored.append((score, candidate))
    if not scored:
        raise SystemExit("No readable benchmark JSON exists yet.")
    return max(scored, key=lambda item: item[0])[1]


def main() -> None:
    runs = sorted(RESULTS.glob("benchmark-*.json"), key=lambda path: path.stat().st_mtime)
    if not runs:
        raise SystemExit("No timestamped benchmark JSON exists yet.")

    # A full current matrix beats an older, wider archive containing adapters
    # that no longer appear in the report. Selective probes remain ineligible.
    run = select_canonical_run(runs, active_reader_ids())
    data = json.loads(run.read_text(encoding="utf-8"))
    data["catalog"] = json.loads(
        (ROOT / "benchmarks" / "products.json").read_text(encoding="utf-8")
    )["products"]
    # The canonical report is an archive of every measured product/workload
    # pair in the selected merged run. Keep launch-only readers and historical
    # readers visible when their timings are present instead of filtering them
    # out based on the current active adapter list.
    data["readers"] = [
        item for item in data["readers"]
        if item.get("product", item.get("name")) not in EXCLUDED_PRODUCTS
    ]
    data["catalog"] = [
        item for item in data["catalog"]
        if item["name"] not in EXCLUDED_PRODUCTS
    ]
    data["measurements"] = [
        item for item in data.get("measurements", [])
        if item.get("product", item.get("reader")) not in EXCLUDED_PRODUCTS
    ]
    report_input = RESULTS / ".canonical-input.json"
    report_input.write_text(json.dumps(data, indent=2), encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "render_report.py"),
            str(report_input),
            str(RESULTS / "benchmark-dashboard.html"),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "render_workload_graphs.py"),
            str(report_input),
            str(RESULTS / "benchmark-workload-graphs.html"),
        ],
        check=True,
    )
    print(f"Updated canonical reports from {run.name}")


if __name__ == "__main__":
    main()
