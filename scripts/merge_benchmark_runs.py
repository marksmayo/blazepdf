#!/usr/bin/env python3
"""Merge verified supplemental measurements into a complete benchmark run."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def key(row: dict) -> tuple[str, str, str]:
    return (row.get("product", row.get("reader", "")), row["work"], row["document"])


def merge(base_path: Path, supplemental_paths: list[Path], output_name: str | None = None) -> dict:
    data = json.loads(base_path.read_text(encoding="utf-8"))
    rows = {key(row): row for row in data["measurements"]}
    # Which run each surviving row came from, so the merged artifact can say
    # what it is made of instead of inheriting the base run's provenance.
    origin = dict.fromkeys(rows, base_path.name)
    sources = [
        {
            "file": base_path.name,
            "role": "base",
            "generated_at": data.get("generated_at"),
        }
    ]
    readers = list(data["readers"])
    reader_keys = {
        (reader.get("product", reader["name"]), reader.get("work"), reader.get("adapter_name", reader["name"]))
        for reader in readers
    }
    for path in supplemental_paths:
        extra = json.loads(path.read_text(encoding="utf-8"))
        sources.append(
            {
                "file": path.name,
                "role": "supplement",
                "generated_at": extra.get("generated_at"),
            }
        )
        for reader in extra.get("readers", []):
            product = reader.get("product", reader["name"])
            reader_key = (product, reader.get("work"), reader.get("adapter_name", reader["name"]))
            if reader_key not in reader_keys:
                readers.append(reader)
                reader_keys.add(reader_key)
        for row in extra.get("measurements", []):
            if row.get("status") == "ok":
                rows[key(row)] = row
                origin[key(row)] = path.name
    data["readers"] = readers
    data["measurements"] = list(rows.values())

    # Provenance. A merged run holds rows measured at different times, so the
    # base run's `generated_at` is not true of the artifact as a whole and a
    # report that printed it dated today's numbers to yesterday. Stamp the
    # merge instead, and keep every source run named alongside the count of
    # rows it actually contributed, so the mixed provenance stays legible.
    contributed = Counter(origin.values())
    for source in sources:
        source["measurements_used"] = contributed.get(source["file"], 0)
    data["merged_from"] = sources
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    data["raw_file"] = output_name or base_path.name
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("supplement", type=Path, nargs="+")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    merged = merge(args.base, args.supplement, args.output.name)
    args.output.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    for source in merged["merged_from"]:
        print(f"  {source['role']:<10} {source['file']}  ->  {source['measurements_used']} rows")


if __name__ == "__main__":
    main()
