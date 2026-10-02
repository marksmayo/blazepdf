#!/usr/bin/env python3
"""Generate Markdown benchmark tables directly from canonical evidence."""
import argparse
import json
from pathlib import Path
from render_workload_graphs import benchmark_cards, medal_counts, placement_grid

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- benchmark-results:start -->", "<!-- benchmark-results:end -->"


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def table(headers, rows):
    return ["| " + " | ".join(map(cell, headers)) + " |",
            "| --- | " + " | ".join("---:" for _ in headers[1:]) + " |"] + [
        "| " + " | ".join(map(cell, row)) + " |" for row in rows]


def case_times(data):
    grouped = {}
    for row in data["measurements"]:
        if row["status"] == "ok":
            case = grouped.setdefault((row["work"], row["document"]), {})
            product = row.get("product", row["reader"])
            case[product] = min(case.get(product, float("inf")), row["median_ms"])
    return grouped


def render(data):
    cards, counts, grid = benchmark_cards(data), medal_counts(data), placement_grid(data)
    ranks = {name: [rank for rank in values.values() if rank is not None] for name, values in grid.items()}
    names = sorted((name for name in ranks if ranks[name]), key=lambda name: (sum(ranks[name]) / len(ranks[name]), name))
    medals = []
    for name in names:
        m, r = counts[name], ranks[name]
        medals.append([name, m['gold'], m['silver'], m['bronze'],
                       len(r) - m['gold'] - m['silver'] - m['bronze'],
                       f"{len(r)} / {len(cards)}", f"{sum(r) / len(r):.2f}"])
    source = data['raw_file']
    summary = ["## Medal / score table", "",
               f"Source: [{source}](results/{source}). {len(cards)} document/workload cards.", "",
               "Score is average rank over successfully measured cards (lower is better), "
               "not an average of incompatible latencies. Missing cards are ignored: "
               "read score alongside coverage. Ties share ranks (1, 1, 3).", ""]
    summary += table(["Product", "Gold", "Silver", "Bronze", "Other placements", "Coverage", "Score ↓"], medals)
    missing = sorted(name for name in ranks if not ranks[name])
    if missing:
        summary += ["", "Catalogued but not measured/scored: " + ", ".join(missing) + "."]
    summary += ["", "## Timing comparisons", "",
                "Median milliseconds, including the declared adapter's launch cost. "
                "Reference is the fastest measured non-BlazePDF product for the same "
                "document/workload. Gap = reference − BlazePDF; ratio = reference / BlazePDF. "
                "Positive gaps and ratios above 1 favor BlazePDF.", "",
                "[Full timing tables for every measured product](docs/benchmark-timings.md)."]
    full = ["# Full benchmark timing tables", "",
            "All values are median milliseconds. Compare only within each document/workload row. "
            "A dash means no successful measurement, not zero. BlazePDF: nine samples "
            "on 2 October 2026. Competitors: retained 30 September rows with five or six samples. "
            "This is not a simultaneous rerun.", "",
            f"Source: [{source}](../results/{source})."]
    grouped = case_times(data)
    for work in sorted({work for work, _ in cards}):
        documents = [doc for candidate, doc in cards if candidate == work]
        comparison = []
        products = sorted({name for doc in documents for name in grouped.get((work, doc), {})}, key=lambda n: (n != "BlazePDF", n))
        for doc in documents:
            times = grouped.get((work, doc), {})
            if "BlazePDF" not in times:
                continue
            blaze = times["BlazePDF"]
            others = sorted((time, name) for name, time in times.items() if name != "BlazePDF")
            if others:
                ref, name = others[0]
                ratio = f"{ref / blaze:.2f}×" if blaze else "—"
                comparison.append([doc, f"{blaze:.3f}", name, f"{ref:.3f}", f"{ref - blaze:+.3f}", ratio])
            else:
                comparison.append([doc, f"{blaze:.3f}", "—", "—", "—", "—"])
        summary += ["", "### " + work, ""] + table(
            ["Document", "BlazePDF (ms)", "Fastest reference", "Reference (ms)", "Gap (ms)", "Ratio"], comparison)
        full += ["", "## " + work, ""] + table(["Document"] + products, [
            [doc] + [f"{grouped.get((work, doc), {})[name]:.3f}" if name in grouped.get((work, doc), {}) else "—" for name in products]
            for doc in documents])
    return "\n".join(summary), "\n".join(full) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads((ROOT / "results/.canonical-input.json").read_text(encoding="utf-8"))
    summary, full = render(data)
    readme, timings = ROOT / "README.md", ROOT / "docs/benchmark-timings.md"
    existing = readme.read_text(encoding="utf-8")
    if existing.count(START) != 1 or existing.count(END) != 1:
        raise ValueError("README must contain exactly one benchmark marker pair")
    before, remainder = existing.split(START)
    _, after = remainder.split(END)
    expected = before + START + "\n\n" + summary + "\n\n" + END + after
    if args.check:
        if existing != expected or not timings.exists() or timings.read_text(encoding="utf-8") != full:
            raise SystemExit("Benchmark documentation is stale; regenerate it")
        print("README scores and all timing tables match canonical evidence")
    else:
        readme.write_text(expected, encoding="utf-8")
        timings.parent.mkdir(parents=True, exist_ok=True)
        timings.write_text(full, encoding="utf-8")
        print("Updated README tables and docs/benchmark-timings.md")


if __name__ == "__main__":
    main()
