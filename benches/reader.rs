//! CPU benchmarks for the `Reader` cost tiers on the pinned corpus.
//!
//! Each tier is measured separately on purpose (see CLAUDE.md): classification,
//! first-page text, and full Markdown extraction are never folded together.
//! Fixtures are read into memory before measuring, so file I/O is excluded.
//!
//! Fixtures are provisioned with `python scripts/bootstrap_benchmark_corpus.py`
//! and the benchmarks must run from the repository root.
//!
//! PDFium rendering is not benchmarked here: it loads a native library at
//! runtime that is not available in CI.

use blazepdf::Reader;
use divan::{black_box, Bencher};

fn main() {
    divan::main();
}

/// Mirrors `benchmarks/corpus.json`.
const DOCUMENTS: &[&str] = &[
    "text",
    "image",
    "duplicate",
    "table",
    "columns",
    "rtl",
    "rotated",
    "signed",
];

fn fixture(id: &str) -> Vec<u8> {
    let path = match id {
        "text" => "vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf",
        "image" => "vendors/CalyPdf/Caly.Benchmarks/fseprd1102849.pdf",
        "duplicate" => "vendors/CalyPdf/Caly.Benchmarks/Document-PublisherError-1.pdf",
        "table" => "vendors/pdf-inspector/tests/fixtures/forecast_table_chart.pdf",
        "columns" => "vendors/pdf-inspector/tests/fixtures/government_positions_women.pdf",
        "rtl" => "vendors/pdf-inspector/tests/fixtures/rtl_hebrew_visual_words.pdf",
        "rotated" => "vendors/sumatrapdf/tests/issue-4839-data/rotated.pdf",
        "signed" => "vendors/sumatrapdf/tests/issue-5581-data/test_sign_PAdES_B-LTA.pdf",
        other => panic!("unknown fixture {other}"),
    };
    std::fs::read(path).unwrap_or_else(|error| {
        panic!(
            "{path}: {error} (run `python scripts/bootstrap_benchmark_corpus.py` \
             and run benchmarks from the repository root)"
        )
    })
}

/// `Reader::inspect_bytes`: classification, page count and signature marker.
#[divan::bench(args = DOCUMENTS)]
fn inspect(bencher: Bencher, id: &str) {
    let bytes = fixture(id);
    bencher.bench_local(|| Reader::inspect_bytes(black_box(&bytes)).unwrap());
}

/// `Reader::first_page_bytes`: first-page text layer only.
#[divan::bench(args = DOCUMENTS)]
fn first_page(bencher: Bencher, id: &str) {
    let bytes = fixture(id);
    bencher.bench_local(|| Reader::first_page_bytes(black_box(&bytes)).unwrap());
}

/// `Reader::open_bytes`: full pipeline including document Markdown.
#[divan::bench(args = DOCUMENTS)]
fn open(bencher: Bencher, id: &str) {
    let bytes = fixture(id);
    bencher.bench_local(|| Reader::open_bytes(black_box(&bytes)).unwrap());
}
