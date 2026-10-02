# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Two things in one tree, and they are coupled:

1. **BlazePDF** — a Rust PDF reader core (`src/`) built on the vendored `pdf-inspector` crate.
2. **A comparative benchmark harness** (`scripts/`, `benchmarks/`) that measures BlazePDF against
   other PDF readers (SumatraPDF, MuPDF, CalyPdf, PDF-XChange, Foxit, browser PDF viewers, …).

The core exists to be measured; every public `Reader` entry point corresponds to a benchmark
workload. When adding a capability to the core, expect to add/adjust a reader entry in
`benchmarks/readers.json` so it is measured on its own terms.

The root is the BlazePDF Git repository. The published `crates/pdf-inspector`
dependency is an ordinary modified-source snapshot, not a submodule. Other local
`vendors/*` checkouts are ignored; do not add their repositories, installers or build
outputs. Third-party corpus PDFs are provisioned by
`scripts/bootstrap_benchmark_corpus.py`, not committed. The harness records each
available vendor's commit via `git -C vendors/<x> rev-parse HEAD`; a source-only
checkout must not confuse the parent BlazePDF revision with the dependency's
upstream revision recorded in NOTICE.md.

## Commands

```powershell
cargo build --release              # both bins; benchmark adapters need the release binaries
cargo test                         # acceptance tests in tests/reader_acceptance.rs
cargo test --test reader_acceptance opens_a_text_pdf   # single test by name substring
cargo run -- --inspect <file.pdf>  # classify only
cargo run -- --first-page <file.pdf>
cargo run --bin blazepdf-window -- <file.pdf>          # egui desktop viewport

python scripts/benchmark.py                        # full run; writes results/ + refreshes canonical reports
python scripts/benchmark.py --reader blazepdf --repeats 3   # repeatable flag, selective probe
python scripts/benchmark.py --no-canonical         # skip canonical report refresh

python scripts/test_benchmark_adapters.py          # adapter command-construction regressions
python scripts/test_workload_graphs.py
python scripts/test_caly_runner.py                 # requires the built CalyRunner
```

Python "tests" are plain scripts with a `main()` and `assert`s — no pytest. They `from benchmark
import …`, which works because `python scripts/<file>.py` puts `scripts/` on `sys.path`.

Rust tests read fixtures by **relative path from the repo root** (`vendors/CalyPdf/...`), so they
only pass when cargo is run from the root.

## Core architecture (`src/lib.rs`)

`Reader` exposes deliberately separate cost tiers, cheapest first. Keeping them separate is the
point — do not let an expensive tier leak into a cheap one:

| Entry point | Work it is allowed to do |
| --- | --- |
| `Reader::inspect` | classification + page count + signature marker; never extracts text |
| `Reader::first_page` | decodes page 1 into a text layer only |
| `Reader::render_first_page` | PDFium raster of page 1 at 150 DPI; no text, no Markdown |
| `Reader::open_viewport` | title + `first_page`, for the initial non-blocking paint |
| `Reader::open` | full pipeline including document Markdown |

Supporting behaviour:

- `first_page_requires_raster` routes image-based or OCR-needed pages away from text extraction so
  OCR never blocks the first paint. `PageTextLayer::requires_raster` carries that decision to the UI.
- `has_signature_marker` scans bytes in 8 KB chunks with a 16-byte overlap (markers can straddle a
  chunk boundary) instead of building an object graph — routing metadata only, **not** signature
  validation.
- `Reader` instances hold a bounded LRU first-page cache (`Mutex<FirstPageCache>` + `VecDeque`
  recency list); capacity `0` disables it. The static methods stay for one-shot CLI/batch use.

`src/bin/blazepdf-window.rs` is the `eframe`/egui viewport and owns all platform rendering; the
library stays portable and hands it a `DesktopViewport`.

## Benchmark harness architecture

`scripts/benchmark.py` is the runner — dense, single-file, intentionally compact. Flow:

1. Load `benchmarks/readers.json` (adapters) × `benchmarks/corpus.json` (8 fixture PDFs).
2. Run each reader's `build` command, if it has one.
3. `command(reader, pdf)` maps `adapter` → an argv list, or a *reason* string it cannot run.
4. `measure()` runs `WARMUPS + repeats` iterations and discards the warm-up.
5. Write `results/benchmark-<UTC stamp>.json` + a self-contained HTML report, then hand off to
   `scripts/update_canonical_reports.py`.

**The central rule of this project: never collapse different workloads into one score.** Every
reader entry carries a `work` label (`classify only`, `open document + first-page text layer`,
`classify + extract markdown`, `render first page at 150 DPI`, `launch to visible document
window`). Reports compare only rows sharing a `work` label. A GUI's time-to-window is never
presented as comparable to Markdown extraction. Unavailable or failing readers are reported as
`skipped`/`failed` **with a reason**, never silently dropped.

### Adapters

`adapter` in `readers.json` selects the measurement strategy in `command()`:
`blazepdf`, `blazepdf-render`, `pdf-inspector`, `caly-core` (dotnet runner, also reports an inner `elapsed_ms`),
`sumatra-bench` / `sumatra-tool-text` / `sumatra-tool-pages`, `mutool-*`, `window-ready`,
`command` (generic `{pdf}` template), and `external-binary` (registered but not runnable).
Add a new strategy by adding a branch to `command()` plus an assertion in
`scripts/test_benchmark_adapters.py`.

`window-ready` is Windows-specific: it launches the reader, polls `EnumWindows` via `ctypes`, and
stops the clock on the first **new, visible** window whose title matches the PDF stem, the
fixture's `window_title`, or the reader's own `window_title`. It then `taskkill`s the process tree.
30 s timeout.

Three title/process pitfalls, each already hit by a real reader:

- Some readers title the window from document metadata, not the filename — those fixtures carry a
  `window_title` in `corpus.json` (RTL Hebrew, Signed PDF).
- Some readers never name the document at all. Slim PDF Reader's title is the constant
  `Slim PDF Reader` with *or* without a document (verified: 1.6 s with no argument, 2.4 s with a
  PDF), so document load is not observable. It matches on a reader-level `window_title` and
  therefore declares a work label that claims only an application window — never put such a reader
  in the document-window group.
- **Many readers are single-instance and open the document in a different process than the one
  launched.** Measured on this machine: Adobe Acrobat, WPS, and PDFgear all open the PDF correctly,
  but the document window belongs to a PID that is not the launched PID. A launcher binary is the
  same trap — `wps.exe /pdf` hands off to a preloaded `wpspdf.exe` and exits 0, so the adapter must
  invoke `wpspdf.exe` directly. Matching on `pid == launched_pid` alone cannot see any of these;
  matching any *new* PID (one absent from the pre-launch `tasklist` snapshot) whose title matches
  is what makes them measurable. A pre-existing instance of such a reader also poisons a run, since
  its window PID predates the snapshot — kill dedicated viewer processes between measurements, but
  never the user's browsers (the Edge/Chrome adapters isolate themselves with `--user-data-dir`).

Executables may be given as `executable` (absolute, or repo-relative) or `executable_env`
(environment variable name). Paths in `readers.json` are currently machine-specific absolute
Windows paths — a missing one yields a `skipped` row, which is the intended behaviour.

### Reporting pipeline

- `update_canonical_reports.py` picks the newest run that covers the complete current active
  reader matrix; a selective `--reader` probe cannot overwrite the full comparison, while stale
  rows for removed readers cannot block a fresh full run. It filters out products no longer in
  `readers.json`/`products.json`, writes `results/.canonical-input.json`, then renders:
  - `results/benchmark-dashboard.html` (`render_report.py`) — per-workload race board, filters, evidence table.
  - `results/benchmark-workload-graphs.html` (`render_workload_graphs.py`) — one card per workload/document, medal counts with competition ranking for ties.
- `merge_benchmark_runs.py` folds verified supplemental runs into a base run, keyed by
  `(product, work, document)`.
- `benchmarks/products.json` is a *catalog* of readers with vendor claims. Catalog membership is
  not a score; claims stay explicitly unverified until measured.

## Adding a reader

`python scripts/add_reader.py https://github.com/owner/project` shallow-clones into `vendors/` and
registers an `external-binary` entry with `work: "not configured"`. It reports nothing until you
give it a real adapter/command and an accurate `work` label. Never invent a `work` label that
overstates what the command actually does.

## Corpus

`benchmarks/corpus.json` points only at fixture PDFs already checked into `vendors/*` — the runner
never downloads opaque test data. Coverage: text-heavy, image, overlapping text, tables, multi-column,
RTL Hebrew, rotated, signed.
