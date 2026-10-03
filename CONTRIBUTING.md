# Contributing

Issues and focused pull requests are welcome. Discuss large API changes first.
For vulnerabilities, follow [SECURITY.md](SECURITY.md), not public issues.

## Setup and checks

Use Windows with Rust/MSVC and Python 3.13. Clone the repository, then run:

```powershell
python scripts/bootstrap_benchmark_corpus.py
python scripts/bootstrap_benchmark_corpus.py --check
cargo test --locked --no-default-features --bin blazepdf --test reader_acceptance -- --skip native_renderer_returns_a_first_page_bitmap
cargo test --locked --no-default-features --test inspection_allocation_budget --test extraction_allocation_budget
python scripts/test_workload_graphs.py
python scripts/test_update_canonical_reports.py
python scripts/test_readme_benchmarks.py
python scripts/update_readme_benchmarks.py --check
```

CI runs these selected checks; it does not run the entire vendored regression
suite, PDFium raster checks, desktop tests or performance benchmarks. Additional
internal fixtures are required for the full PDF core suite.

The command explicitly excludes one PDFium-dependent test. With a compatible
PDFium runtime installed and `PDFIUM_LIB_PATH` configured, run the full acceptance
suite without `--skip` before changing rendering behavior.

## Red / green / refactor

1. Add a focused regression test and run it against unchanged production code.
   Confirm it fails for the intended reason, not missing fixtures or dependencies.
2. Make the smallest correct change and run the test again to confirm green.
3. Refactor while keeping tests green, then run the relevant checks above.

For optimizations, include before/after release measurements with identical
fixtures and settings, retained samples, and output-equality checks. Allocation
gates are useful but do not alone prove faster execution. Do not weaken correctness
or select historical per-card bests to improve a medal count.

Edit the published PDF core in `crates/pdf-inspector/`, not ignored local vendor
clones. Keep third-party notices intact. Do not commit downloaded PDFs, binaries,
credentials or machine-specific paths. Generated benchmark tables must be updated
through `scripts/update_readme_benchmarks.py`, not hand-edited.

In your PR, explain the problem, scope, red/green evidence, validation and remaining
limitations. Do not claim support for an untested platform.
