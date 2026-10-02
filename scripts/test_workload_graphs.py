"""Regression check for workload graphs: no registered reader may disappear."""

from __future__ import annotations

from render_workload_graphs import benchmark_cards, medal_counts, render


def main() -> None:
    data = {
        "generated_at": "2026-01-01T00:00:00Z",
        "repeats": 3,
        "benchmark_note": "Concurrent-load benchmark; compare stressed-system timings only.",
        "readers": [
            {"name": "BlazePDF", "work": "classify only"},
            {"name": "pdf-inspector", "work": "classify + extract markdown"},
            {"name": "CalyPdf core", "work": "open document + first-page text layer"},
            {"name": "SumatraPDF", "work": "launch to visible document window"},
        ],
        "measurements": [
            {
                "reader": "BlazePDF",
                "work": "classify only",
                "document": "Text-heavy",
                "status": "ok",
                "median_ms": 10,
            }
        ],
    }
    graph = render(data)
    mixed = {
        **data,
        "repeats": 5,
        "measurements": [
            {**data["measurements"][0], "samples_ms": [10] * 9},
            {"reader": "pdf-inspector", "work": "classify + extract markdown",
             "document": "Text-heavy", "status": "ok", "median_ms": 20,
             "samples_ms": [20] * 5},
        ],
    }
    assert "5 to 9 measured runs per case (mixed sample counts)" in render(mixed)
    assert "3 measured runs per case" in graph  # Legacy rows without sample arrays.
    uniform = {**data, "repeats": 99,
               "measurements": [{**data["measurements"][0], "samples_ms": [10] * 3}]}
    assert "3 measured runs per case" in render(uniform)
    failed = {**data["measurements"][0], "status": "failed", "samples_ms": [10]}
    assert "5 to 9 measured runs per case (mixed sample counts)" in render(
        {**mixed, "measurements": mixed["measurements"] + [failed]})
    assert "no successful measured runs" in render({**data, "measurements": [failed]})
    for reader in ("BlazePDF", "pdf-inspector", "CalyPdf core", "SumatraPDF"):
        assert reader in graph, f"{reader} vanished from graph data"
    assert "const PRODUCTS" in graph
    assert "not benchmarked" in graph
    assert 'id="not-benchmarked-count"' in graph
    assert 'id="product-count"' in graph
    assert "PRODUCTS.length" in graph
    assert "missingCount" in graph
    assert '<div class="note benchmark-note"><strong>Benchmark note:</strong> Concurrent-load benchmark; compare stressed-system timings only.</div>' in graph
    assert "PDFgear" in render({"generated_at": "now", "repeats": 1,
                                "readers": [{"name": "BlazePDF"}],
                                "catalog": [{"name": "PDFgear", "kind": "reader", "platforms": "Windows",
                                             "features": "OCR", "claim": "fast (unverified)",
                                             "source": "https://example.com", "tests": ["OCR latency"]}],
                                "measurements": [{"reader": "BlazePDF", "product": "BlazePDF", "work": "open",
                                                  "document": "PDF", "status": "ok", "median_ms": 1}]} )
    assert 'id="medal-totals"' not in graph
    assert 'id="medal-head"' in graph
    assert 'D.benchmark_cards.map' in graph
    assert 'placement_grid' in graph
    assert 'Score' in graph
    assert 'average.toFixed(2)' in graph
    assert 'rowScore(a)-rowScore(b)' in graph
    assert 'rank-gold' in graph
    assert 'rank-silver' in graph
    assert 'rank-bronze' in graph

    cards = benchmark_cards(
        {
            "measurements": [
                {"work": "classify only", "document": "Text-heavy"},
                {"work": "classify only", "document": "RTL Hebrew"},
                {"work": "launch to visible document window", "document": "Text-heavy"},
            ]
        }
    )
    assert cards == [
        ("classify only", "RTL Hebrew"),
        ("classify only", "Text-heavy"),
        ("launch to visible document window", "Text-heavy"),
    ]

    assert medal_counts(
        {
            "readers": [{"name": "BlazePDF"}, {"name": "CalyPdf"}],
            "measurements": [
                {"reader": "BlazePDF", "work": "open", "document": "A", "status": "ok", "median_ms": 10},
                {"reader": "CalyPdf", "work": "open", "document": "A", "status": "ok", "median_ms": 20},
                {"reader": "BlazePDF", "work": "open", "document": "B", "status": "ok", "median_ms": 30},
                {"reader": "CalyPdf", "work": "open", "document": "B", "status": "ok", "median_ms": 5},
            ],
        }
    ) == {
        "BlazePDF": {"gold": 1, "silver": 1, "bronze": 0, "fourth": 0, "fifth": 0, "sixth": 0},
        "CalyPdf": {"gold": 1, "silver": 1, "bronze": 0, "fourth": 0, "fifth": 0, "sixth": 0},
    }

    # Equal median times share a placement; medals use competition ranking (1, 1, 3).
    assert medal_counts(
        {
            "readers": [{"name": "A"}, {"name": "B"}, {"name": "C"}, {"name": "D"}, {"name": "E"}, {"name": "F"}, {"name": "G"}],
            "measurements": [
                {"reader": "A", "work": "open", "document": "Tied", "status": "ok", "median_ms": 10},
                {"reader": "B", "work": "open", "document": "Tied", "status": "ok", "median_ms": 10},
                {"reader": "C", "work": "open", "document": "Tied", "status": "ok", "median_ms": 20},
                {"reader": "D", "work": "open", "document": "Tied", "status": "ok", "median_ms": 30},
                {"reader": "E", "work": "open", "document": "Tied", "status": "ok", "median_ms": 40},
                {"reader": "F", "work": "open", "document": "Tied", "status": "ok", "median_ms": 50},
                {"reader": "G", "work": "open", "document": "Tied", "status": "ok", "median_ms": 60},
            ],
        }
    ) == {
        "A": {"gold": 1, "silver": 0, "bronze": 0, "fourth": 0, "fifth": 0, "sixth": 0, "place_7": 0},
        "B": {"gold": 1, "silver": 0, "bronze": 0, "fourth": 0, "fifth": 0, "sixth": 0, "place_7": 0},
        "C": {"gold": 0, "silver": 0, "bronze": 1, "fourth": 0, "fifth": 0, "sixth": 0, "place_7": 0},
        "D": {"gold": 0, "silver": 0, "bronze": 0, "fourth": 1, "fifth": 0, "sixth": 0, "place_7": 0},
        "E": {"gold": 0, "silver": 0, "bronze": 0, "fourth": 0, "fifth": 1, "sixth": 0, "place_7": 0},
        "F": {"gold": 0, "silver": 0, "bronze": 0, "fourth": 0, "fifth": 0, "sixth": 1, "place_7": 0},
        "G": {"gold": 0, "silver": 0, "bronze": 0, "fourth": 0, "fifth": 0, "sixth": 0, "place_7": 1},
    }
    wide = render({"generated_at": "now", "repeats": 1,
                   "readers": [{"name": f"Reader {i}"} for i in range(1, 27)],
                   "measurements": [{"reader": f"Reader {i}", "product": f"Reader {i}", "work": "open", "document": "PDF", "status": "ok", "median_ms": i} for i in range(1, 27)]})
    assert "26th" in wide
    assert 'class="table-scroll"' not in wide
    assert "max-width:none" in wide
    assert "table-layout:fixed;width:100%" in wide
    assert "$('place-count')" not in wide
    assert "$('medal-head').innerHTML" in wide
    assert "cards.map" in wide

    reduced = render({"generated_at": "now", "repeats": 1,
                      "readers": [{"name": "Reader 1"}],
                      "catalog": [{"name": "Reader 2", "kind": "reader"}],
                      "measurements": [{"reader": "Reader 1", "product": "Reader 1", "work": "open", "document": "PDF", "status": "ok", "median_ms": 1}]})
    assert 'Product' in reduced
    assert 'Total' in reduced
    assert 'Score' in reduced


if __name__ == "__main__":
    main()
