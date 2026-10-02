# BlazePDF

[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen)](https://github.com/marksmayo/blazepdf/issues)
[![Star to support](https://img.shields.io/github/stars/marksmayo/blazepdf?style=flat&label=star%20to%20support)](https://github.com/marksmayo/blazepdf)
[![MIT license](https://img.shields.io/github/license/marksmayo/blazepdf)](LICENSE)
[![Verified checks passing](https://img.shields.io/badge/verified_checks-passing-brightgreen)](#verification)
[![Rust tested 1.98.0](https://img.shields.io/badge/Rust-tested%201.98.0-orange?logo=rust)](#build-and-run)
[![Python tested 3.13.2](https://img.shields.io/badge/Python-tested%203.13.2-blue?logo=python&logoColor=white)](#build-and-run)
[![Benchmark gold 40/40](https://img.shields.io/badge/benchmark_gold-40%2F40-gold)](#medal--score-table)
[![Rust tracked lines 140,050](https://img.shields.io/badge/Rust_lines-140%2C050-orange?logo=rust)](#repository-line-counts)
[![Python tracked lines 1,644](https://img.shields.io/badge/Python_lines-1%2C644-blue?logo=python&logoColor=white)](#repository-line-counts)
[![HTML tracked lines 11](https://img.shields.io/badge/HTML_lines-11-E34F26?logo=html5&logoColor=white)](#repository-line-counts)

A benchmark-driven Rust PDF reader core, CLI, and lightweight desktop viewport.
Classification, first-page text, native rendering, and full Markdown extraction are
separate cost tiers: opening a document need not pay for every capability at once.

**Latest snapshot: 40 gold medals across 40 benchmark cards.** Eight documents ×
five workloads, with nine measured samples per BlazePDF card and one excluded warmup.
This describes this corpus and machine—not every PDF, feature set, or computer.

## Capabilities

- Classification and page count without building Markdown.
- First-page text layers with rotation information and bounded interactive caching.
- Image/ambiguous-page routing to raster without blocking first paint on OCR.
- First-page rendering at 150 DPI through a separately supplied PDFium runtime.
- Structured Markdown extraction and a minimal egui desktop viewport.

The signature marker is routing metadata, **not cryptographic signature validation**.
BlazePDF is experimental, not a feature-equivalent replacement for commercial editors.
Output-equality checks compare before/after BlazePDF builds; the benchmark does not
establish identical rendering quality across different products.

## Build and run

Measured environment: Windows 11, Intel Core i7-12700H (20 logical CPUs), 31.7 GB RAM,
Rust 1.98.0, Python 3.13.2, release builds. The benchmark harness uses Windows-specific
executables/window detection; other platforms were not measured in this snapshot.

Install Rust and the MSVC C++ build tools on Windows, then:

```powershell
git clone https://github.com/marksmayo/blazepdf.git
cd blazepdf
cargo build --release --locked
```

For the library and CLI without the GUI feature:

```powershell
cargo build --release --locked --no-default-features --bin blazepdf
```

```powershell
.\target\release\blazepdf.exe --inspect document.pdf
.\target\release\blazepdf.exe --first-page document.pdf
.\target\release\blazepdf.exe document.pdf
.\target\release\blazepdf.exe --render document.pdf page.ppm
.\target\release\blazepdf-window.exe document.pdf
```

Native rendering and viewport raster fallback require a compatible PDFium library.
Set `PDFIUM_LIB_PATH` to its library path if automatic discovery cannot find it.
PDFium and other vendors' installers are not bundled.

## Benchmark methodology and limitations

BlazePDF's latest measurements are from **2 October 2026** (NZDT). Competitor rows
retain the **30 September 2026** reference. This is a mixed-date snapshot, not a fresh
simultaneous rerun of every competitor. Other applications were running during
development, and launch timings vary. Competitors have five or six samples per
successful row; BlazePDF has nine. All retained samples are in the raw JSON.

Only identical document/workload pairs are compared. Classification, first-page
text, Markdown extraction, 150-DPI rendering and launch-to-visible-window stay
separate. Missing/failed measurements are not zero or losses. BlazePDF's matrix
uses one complete run, not a collection of historical per-card bests.

The following scores and timings are generated directly from canonical evidence.

<!-- benchmark-results:start -->

## Medal / score table

Source: [benchmark-20261002T072651Z-merged.json](results/benchmark-20261002T072651Z-merged.json). 40 document/workload cards.

Score is average rank over successfully measured cards (lower is better), not an average of incompatible latencies. Missing cards are ignored: read score alongside coverage. Ties share ranks (1, 1, 3).

| Product | Gold | Silver | Bronze | Other placements | Coverage | Score ↓ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BlazePDF | 40 | 0 | 0 | 0 | 40 / 40 | 1.00 |
| MuPDF | 0 | 30 | 5 | 5 | 40 / 40 | 2.45 |
| PDF24 Reader | 0 | 1 | 7 | 0 | 8 / 40 | 2.88 |
| pdf-inspector | 0 | 8 | 8 | 7 | 23 / 40 | 3.04 |
| PDF24 bundled qpdf | 0 | 0 | 2 | 6 | 8 / 40 | 4.38 |
| SumatraPDF | 0 | 1 | 9 | 14 | 24 / 40 | 4.54 |
| Google Chrome PDF viewer | 0 | 0 | 0 | 8 | 8 / 40 | 4.62 |
| Okular | 0 | 0 | 0 | 6 | 6 / 40 | 4.67 |
| CalyPdf | 0 | 0 | 1 | 23 | 24 / 40 | 4.96 |
| Foxit PDF Reader | 0 | 0 | 0 | 8 | 8 / 40 | 6.00 |
| Sejda PDF Desktop | 0 | 0 | 0 | 8 | 8 / 40 | 6.62 |
| Xodo PDF Reader | 0 | 0 | 0 | 8 | 8 / 40 | 8.75 |

Catalogued but not measured/scored: Adobe Acrobat Reader.

## Timing comparisons

Median milliseconds, including the declared adapter's launch cost. Reference is the fastest measured non-BlazePDF product for the same document/workload. Gap = reference − BlazePDF; ratio = reference / BlazePDF. Positive gaps and ratios above 1 favor BlazePDF.

[Full timing tables for every measured product](docs/benchmark-timings.md).

### classify + extract markdown

| Document | BlazePDF (ms) | Fastest reference | Reference (ms) | Gap (ms) | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Financial table | 22.112 | MuPDF | 28.259 | +6.147 | 1.28× |
| Image document | 270.299 | MuPDF | 298.699 | +28.400 | 1.11× |
| Multi-column | 26.242 | pdf-inspector | 69.790 | +43.548 | 2.66× |
| Overlapping text | 18.367 | MuPDF | 80.300 | +61.933 | 4.37× |
| RTL Hebrew | 16.577 | pdf-inspector | 34.018 | +17.441 | 2.05× |
| Rotation | 16.893 | MuPDF | 35.139 | +18.246 | 2.08× |
| Signed PDF | 20.909 | MuPDF | 46.613 | +25.704 | 2.23× |
| Text-heavy | 31.393 | MuPDF | 38.074 | +6.681 | 1.21× |

### classify only

| Document | BlazePDF (ms) | Fastest reference | Reference (ms) | Gap (ms) | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Financial table | 12.381 | pdf-inspector | 22.855 | +10.474 | 1.85× |
| Image document | 21.419 | MuPDF | 23.506 | +2.087 | 1.10× |
| Multi-column | 14.033 | MuPDF | 20.671 | +6.638 | 1.47× |
| Overlapping text | 18.301 | MuPDF | 24.308 | +6.007 | 1.33× |
| RTL Hebrew | 14.543 | pdf-inspector | 27.489 | +12.946 | 1.89× |
| Rotation | 13.050 | MuPDF | 21.672 | +8.622 | 1.66× |
| Signed PDF | 16.811 | MuPDF | 29.015 | +12.204 | 1.73× |
| Text-heavy | 13.455 | MuPDF | 14.389 | +0.934 | 1.07× |

### launch to visible document window

| Document | BlazePDF (ms) | Fastest reference | Reference (ms) | Gap (ms) | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Financial table | 20.593 | MuPDF | 115.028 | +94.435 | 5.59× |
| Image document | 20.455 | PDF24 Reader | 372.615 | +352.160 | 18.22× |
| Multi-column | 20.254 | MuPDF | 90.327 | +70.073 | 4.46× |
| Overlapping text | 20.287 | MuPDF | 128.300 | +108.013 | 6.32× |
| RTL Hebrew | 21.606 | MuPDF | 44.140 | +22.534 | 2.04× |
| Rotation | 20.355 | MuPDF | 72.137 | +51.782 | 3.54× |
| Signed PDF | 20.033 | MuPDF | 72.812 | +52.779 | 3.63× |
| Text-heavy | 19.940 | MuPDF | 67.089 | +47.149 | 3.36× |

### open document + first-page text layer

| Document | BlazePDF (ms) | Fastest reference | Reference (ms) | Gap (ms) | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Financial table | 16.066 | pdf-inspector | 40.013 | +23.947 | 2.49× |
| Image document | 190.402 | SumatraPDF | 259.716 | +69.314 | 1.36× |
| Multi-column | 16.149 | pdf-inspector | 23.606 | +7.457 | 1.46× |
| Overlapping text | 19.844 | pdf-inspector | 47.337 | +27.493 | 2.39× |
| RTL Hebrew | 13.055 | MuPDF | 25.190 | +12.135 | 1.93× |
| Rotation | 12.890 | pdf-inspector | 39.541 | +26.651 | 3.07× |
| Signed PDF | 17.627 | MuPDF | 39.021 | +21.394 | 2.21× |
| Text-heavy | 24.715 | MuPDF | 56.882 | +32.167 | 2.30× |

### render first page at 150 DPI

| Document | BlazePDF (ms) | Fastest reference | Reference (ms) | Gap (ms) | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Financial table | 43.791 | MuPDF | 107.538 | +63.747 | 2.46× |
| Image document | 634.231 | MuPDF | 2504.587 | +1870.356 | 3.95× |
| Multi-column | 32.257 | MuPDF | 143.759 | +111.502 | 4.46× |
| Overlapping text | 126.200 | MuPDF | 300.778 | +174.578 | 2.38× |
| RTL Hebrew | 30.395 | MuPDF | 72.218 | +41.823 | 2.38× |
| Rotation | 35.906 | MuPDF | 154.254 | +118.348 | 4.30× |
| Signed PDF | 35.599 | MuPDF | 131.809 | +96.210 | 3.70× |
| Text-heavy | 46.059 | MuPDF | 143.413 | +97.354 | 3.11× |

<!-- benchmark-results:end -->

## Reports and evidence

- [Interactive workload graphs and medal/score board](results/benchmark-workload-graphs.html).
- [Interactive dashboard and distribution statistics](results/benchmark-dashboard.html).
- [All-products timing tables](docs/benchmark-timings.md).
- [Latest 40 BlazePDF measurements](results/benchmark-20261002T072651Z.json).
- [Complete comparison snapshot](results/benchmark-20261002T072651Z-merged.json).
- [Unchanged competitor reference](results/benchmark-20260930T040051Z-merged.json).
- [Ranked optimization candidates and implementation evidence](results/remaining-classification-100-optimizations.md).

GitHub displays HTML source rather than executing these reports. Download either
HTML file and open it locally for the interactive view; Markdown tables work on GitHub.

## Reproduce the corpus, tests and benchmarks

Third-party PDFs are not redistributed. Download the eight commit-pinned corpus
files and verify their hashes before running acceptance tests or benchmarks:

```powershell
python scripts/bootstrap_benchmark_corpus.py
python scripts/bootstrap_benchmark_corpus.py --check
cargo test --no-default-features --bin blazepdf --test reader_acceptance
cargo test --no-default-features --test inspection_allocation_budget --test extraction_allocation_budget
python scripts/test_workload_graphs.py
python scripts/test_update_canonical_reports.py
python scripts/test_readme_benchmarks.py
python scripts/update_readme_benchmarks.py --check
```

Our modified `pdf-inspector` is preserved as ordinary source: no submodule setup is
required. The eight-file bootstrap supplies the top-level acceptance suite. Its
larger internal regression suite needs additional upstream fixtures not provisioned
by this bootstrap.

With PDFium configured, rerun the full five-workload BlazePDF matrix:

```powershell
python scripts/benchmark.py --reader blazepdf-first-page --reader blazepdf-inspect --reader blazepdf-render --reader blazepdf --reader blazepdf-window --repeats 9 --no-canonical
```

To compare the whole new run with the retained reference, replace `<new-run>` with
its timestamped filename:

```powershell
python scripts/merge_benchmark_runs.py results/benchmark-20260930T040051Z-merged.json results/<new-run>.json results/<new-run>-merged.json
python scripts/update_canonical_reports.py
python scripts/update_readme_benchmarks.py
```

For a fresh all-product comparison, install/configure the readers in
`benchmarks/readers.json`, then run `python scripts/benchmark.py`. Executable paths
in that manifest describe the original machine: update them for your installation.
Missing installations are recorded as skipped. Other vendors' software is not bundled.

## Layout

| Path | Purpose |
| --- | --- |
| `src/` | Reader core, CLI and viewport |
| `crates/pdf-inspector/` | Modified PDF core and bundled CMaps |
| `tests/` | Acceptance and allocation regression gates |
| `benchmarks/` | Corpus, pinned fixture sources and reader/product configuration |
| `scripts/` | Benchmarks, comparisons and report/documentation generation |
| `results/` | Published final raw evidence and standalone reports |
| `docs/benchmark-timings.md` | Timings for every measured product |

## Repository line counts

The line-count badges are a snapshot of physical lines in Git-tracked `.rs`, `.py`
and `.html` files, including comments and blank lines. Rust includes the modified
vendored PDF core and tests (83 files); Python covers the harness, generators and
tests (21 files). HTML covers the two generated, minified benchmark reports (11
physical lines), not HTML templates embedded in Python strings. These are file-line
counts, not executable-code counts or live CI metrics. Untracked vendor checkouts,
build outputs and downloaded fixtures are excluded.

## License and attribution

BlazePDF's own code is [MIT licensed](LICENSE). The Firecrawl PDF core, Adobe CMaps,
downloaded documents and runtime dependencies retain their notices and terms.
See [NOTICE.md](NOTICE.md) for source provenance and attribution.

## Verification

The **verified checks passing** badge records the local publication checks on
2 October 2026: three Rust CLI tests, 18 reader acceptance tests, both allocation
regression gates, three Python documentation/fixture tests, workload-graph checks,
and both canonical-report selection tests. The README timing tables also match the
canonical JSON, and all eight commit-pinned upstream fixture hashes were verified.

This is a verified snapshot, **not a live CI badge or a claim that every optional
test in the repository has run**. Rust and Python badges show the tested toolchain
versions, not minimum supported versions. The gold badge describes the published
benchmark snapshot and its methodology above.

Contributions are welcome: [open an issue](https://github.com/marksmayo/blazepdf/issues)
to discuss a change, or submit a pull request with focused tests. If this project is
useful to you, click **Star** at the top of the repository to support it.
