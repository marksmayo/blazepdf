# Benchmark methodology

The canonical input is recorded in `results/.canonical-input.json`. See the
[full timing tables](benchmark-timings.md) and README for raw evidence links.

## Snapshot and protocol

- BlazePDF: 2 October 2026 NZDT, one complete run of eight documents and five
  distinct workloads, nine measured repetitions per card plus excluded warmup.
- Competitors: retained 30 September reference, five or six successful samples.
  This is not a simultaneous all-product rerun.
- Windows 11, Intel Core i7-12700H, 31.7 GB RAM, release binaries. Other applications
  ran during development; scheduling and launch noise remain limitations.
- Latencies are medians in milliseconds and include each adapter's declared launch
  cost. Classification, Markdown, first-page text, 150-DPI raster and visible-window
  launch are separate workloads, not interchangeable operations.
- Only matching document/workload pairs compete. Missing and failed rows are not
  zero or losses. Multiple adapters for one product use its best adapter per card.
- Ties use competition ranking (1, 1, 3). Score is average rank over successful
  cards; compare it with coverage, not in isolation.

The compact README chart shows only classification medians from this fixed
snapshot; it is not a geometric mean, aggregate speedup or live result.

## Correctness and limitations

Before/after output checks compare BlazePDF builds, not equivalent feature sets or
rendering quality between products. Eight selected PDFs cannot establish universal
performance. Signature markers do not establish valid signatures. No statistical
significance or universal superiority is claimed by a narrow timing win.

## Reproduction

Follow the README's corpus bootstrap, build, benchmark and merge commands. Supply
PDFium separately for rendering and configure installed competitor paths in
`benchmarks/readers.json`. Retain all samples, environment details and failures.
Use one whole BlazePDF run, not historical per-card minimums. Regenerate canonical
reports and Markdown tables through their scripts, and record any stale comparison
rows explicitly. Update the fixed SVG chart when changing the snapshot.
