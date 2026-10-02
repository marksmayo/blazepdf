# Remaining classification: 100 ranked optimization candidates

Current scope: `benchmark-20261002T072651Z-merged.json` has **40 gold / 0 silver**. All 40 BlazePDF workloads succeeded with nine measured samples each. Text-heavy classification is 13.455 ms versus stored MuPDF 14.389 ms. The text-heavy PDF is 21,157 bytes and one page, with a compressed content stream, object stream, and clipping-heavy text. Initial investigation used an older 14.824 ms sample; cold-launch variation remains substantial. The report uses this complete matrix, not historical per-card bests. Competitor rows remain the unchanged September 30 reference; this result is not a fresh simultaneous rerun of every competitor.

These are ranked candidates, not 100 claimed or guaranteed wins. The order combines expected impact, reachability from the inspect path, and correctness risk. Some are already present and need verification; build experiments may be rejected. Implement cohesive slices only when evidence supports a gain, with a failing behavioral/performance gate before the change and correctness verification afterward. Do not weaken classification, special-case fixtures, suppress samples, alter competitor rows, or stop unrelated programs to obtain medals.

Initial measurements: current 64-run proof build measured 15.57 ms (25 repeats); a one-thread environment probe measured 16.73 ms under changing external CPU load. Thread-count evidence is inconclusive. Existing routing first probes all selected pages; an inconclusive result leads to another proof in `analyze_page_content_for_launch`. `BytePresence::ascii_alphanumeric_count` scans all 256 possible bytes.

## Highest-priority routing and startup candidates

1. Remove the second clear-text probe when the first document-level proof falls back; pass its evidence into exact routing.
2. Replace 256 byte-by-byte alphanumeric membership checks with three masked population counts.
3. Reuse the parsed page map throughout classification instead of traversing the page tree again.
4. Reuse the selected-page scan plan between the proof and exact routing.
5. Return a route-only classification without decoding document information.
6. Use sequential object parsing for small PDFs, where worker startup can exceed useful parsing time.
7. Select sequential versus parallel parsing by xref object count rather than fixture identity.
8. Avoid initializing Rayon for one-page classify-only work.
9. Keep large-document extraction parallel while reducing small-document parser startup.
10. Measure and reduce dynamic imports reachable from the inspect CLI.
11. Keep renderer initialization lazy so classify-only runs never load PDFium.
12. Compare a compact inspect binary with the shared CLI using paired, interleaved measurements.
13. Buffer inspect stdout so the complete metadata answer requires one write.
14. Use an explicit stdout lock for metadata emission.
15. Avoid spawning Markdown warmup threads in any classification entry point.
16. Remove redundant byte validation once a validated buffer reaches the loader.
17. Preserve borrowed input through loader prechecks and repairs.
18. Use SIMD substring searches for all container prechecks on the inspect path.
19. Skip struct-tree rewriting when no malformed-name candidate exists.
20. Avoid repeated file metadata calls around a one-shot inspect read.

## Content scanning and evidence reuse

21. Cache decompressed sampled content within a single classification operation.
22. Borrow unfiltered stream content instead of cloning it.
23. Avoid a masked content allocation for ordinary strings/comments.
24. Stop updating character-presence bits once sufficient diversity has been established.
25. Skip literal-string bodies with delimiter searches after diversity is established.
26. Skip comment bodies with a newline search.
27. Skip PDF names without checking each name character for operators.
28. Use a byte lookup table for whitespace/delimiter classification.
29. Dispatch operator tokens by length before comparing their bytes.
30. Recognize Tj/TJ in one compact token check.
31. Count single-byte path operators without repeated slice comparisons.
32. Fuse path/text/XObject counts into one pass.
33. Reject ambiguous render-mode operators before collecting expensive evidence.
34. Carry render mode across content-array boundaries.
35. Carry text evidence across content-array boundaries.
36. Avoid re-inflating a stream after an inconclusive proof.
37. Retain the proof's used-font names for the exact fallback.
38. Retain the proof's XObject names for the exact fallback.
39. Pre-size stream-part collections from Contents array length.
40. Avoid joining independently readable streams for classification.
41. Maintain one bounded decompression budget across sampled page streams.
42. Use faster inflation only where the existing decompression bound remains enforced.
43. Reuse decompressor allocation for successive small streams.
44. Probe content-stream filter names once rather than on each fallback.
45. Resolve indirect stream Length values once.
46. Stop after decisive text only when later streams cannot change the classification.
47. Keep graphics-heavy text shortcuts bounded by path-to-text evidence.
48. Require malformed/unresolved resource entries to fall back conservatively.
49. Avoid scanning strings inside marked-content dictionaries as painted text.
50. Count only nonempty text-show operands as text evidence.

## Page trees, resources, fonts and repairs

51. Resolve inherited Resources once per sampled page.
52. Borrow resource dictionaries rather than cloning them.
53. Reuse the resource chain between fonts and XObjects.
54. Cache indirect XObject subtype resolution within one classification.
55. Avoid image-pixel inventory when visible text conclusively determines the route.
56. Avoid Form inventory only after proving no bound Forms can affect classification.
57. Reuse executed-content coverage in the exact fallback.
58. Preserve authoritative parsed page count instead of rescanning raw /Page markers.
59. Use a range rather than a vector for full-page scan plans.
60. Special-case a one-page selected plan without allocating a page vector.
61. Use a fixed small array for a three-page sampling plan.
62. Deduplicate configured pages once.
63. Reject out-of-range configured pages before content loading.
64. Avoid collecting OCR page lists for route-only callers.
65. Avoid constructing OCR explanation strings for route-only callers.
66. Cache used-font classification per page.
67. Skip unused-font decoding when its result cannot change the route.
68. Resolve font subtype references once.
69. Reuse ToUnicode availability evidence without parsing full CMaps.
70. Keep Type3/undecodable-font safeguards on ambiguous pages.
71. Skip malformed-BBox repair scans when all referenced objects loaded correctly.
72. Cache object-stream decompression used by repair fallbacks.
73. Skip Form BBox widening when no Form XObject exists.
74. Borrow unchanged repaired byte buffers with Cow.
75. Avoid container repair candidate generation until the ordinary parse fails.
76. Generate repair candidates lazily instead of allocating all candidates up front.
77. Stop repair attempts on definitive encryption errors.
78. Build sorted object-offset indexes once for repeated boundary lookups.
79. Use binary search for successor object offsets.
80. Reuse xref compressed-object container indexes across object-stream processing.

## Allocation, build, and measurement candidates

81. Pre-size small object-id maps from known xref cardinality.
82. Use contiguous small collections for sampled-page state.
83. Eliminate locks around state used only by a sequential loader.
84. Avoid temporary vectors when validating a resource inventory.
85. Remove repeated clock reads from inner classification loops.
86. Keep optional profiling environment lookups outside hot loops.
87. Use cached SIMD searchers for repeated marker needles.
88. Fuse signature candidate discovery with existing raw-byte prechecks where practical.
89. Retain exact signature prefix checks after SIMD candidate discovery.
90. Avoid a second signature/file read in cached inspect APIs.
91. Measure codegen-unit alternatives against cold-process launch.
92. Measure thin LTO against non-LTO with identical correctness checks.
93. Measure size optimization only if loader cost dominates.
94. Measure static CRT linking using paired timing and binary import evidence.
95. Measure function/section layout improvements with a reproducible profile.
96. Use profile-guided optimization trained on diverse classification documents.
97. Preserve native OS command-line paths with args_os, avoiding their UTF-8 String conversion before Reader's path interface.
98. Format bounded inspection metadata in a checked stack buffer instead of allocating the current temporary String; retain exact output and I/O error handling.
99. Consume contiguous numeric/whitespace runs in the route scanner instead of redispatching every ignored byte.
100. Count the loader's page iterator directly instead of allocating a map solely to obtain its length.

Verification requirements (not counted as performance optimizations): retain text/image/mixed/signed/malformed acceptance coverage, assert cold release latency and real metadata, use alternating-order paired comparisons, keep all measured samples, and publish complete 40-card runs with unchanged competitor rows. Candidates 97–100 replace the original four verification-only entries so the numbered list contains optimization hypotheses rather than padding its count with tests.

## Source anchors and evidence limits

- Candidates 1–9 and 58–65: `detector.rs::detect_routing_from_document`, `PageScanPlan`, the loader's `finish_loaded_document`, and the lopdf feature selection in the vendor manifest. These are on the real `Reader::inspect_bytes -> detect_pdf_mem_scoped -> detect_pdf_routing_mem_with_config` path. Sequential parsing and the duplicated-probe removal have paired timing evidence below; scan plans already avoid full-range materialization. Page-map reuse is an alternative to direct counting, not an additional proven saving.
- Candidates 10–15, 91–98: `src/main.rs`, `Cargo.toml` release policy, `.cargo/config.toml`, PE import evidence and cold-process probes below. Inspect does not enter the Markdown warmup or renderer paths. Those exclusions are invariants to verify, not newly implemented wins. The compact executable experiment was rejected; static CRT and pooled stdout were retained with measurements. args_os and stack formatting remain unmeasured hypotheses.
- Candidates 16–20 and 71–80: `load_document_from_mem_with_repairs`, `load_document_bytes`, `repair_pdf_container_candidates`, `overlong_numerals::saturate_overlong_bbox_numerals`, and `recover_referenced_bboxes_in_object_streams`. The ordinary parse already precedes container repair generation; recovery already returns early when no referenced BBoxes are missing. Those existing fast paths should not be counted as new changes. Repair laziness affects damaged PDFs, not the currently clean text-heavy fixture. The normal-xref completeness proof has a deterministic allocation gate below.
- Candidates 21–50 and 99: `detector/content_scan.rs::probe_clear_text_page`, `scan_route_text_stream`, `scan_page`, and `detector.rs::scan_page_content_evidence`. The route probe inflates streams and tracks operator counts/diversity; the exact fallback handles cross-stream graphics state and forms. This establishes where inflation/evidence reuse can save work, not that every cache or early exit is safe or beneficial. Numeric-run batching is implemented and measured below; changing safety thresholds is excluded.
- Candidates 51–57 and 66–70: `content_scan.rs::resource_chain`, `page_xobjects_are_images`, `detector.rs::resolve_with_shadowing`, `resolve_font_names_to_ids`, `font_decoder`, and `resources_bind_no_form_xobjects`. These functions anchor resource borrowing/caching hypotheses. Ambiguous fonts, inherited resources and unpainted/invisible text still require conservative fallback; a resource-name shortcut alone is insufficient evidence.
- Candidates 81–90: the same loader/scanner collection sites plus `src/lib.rs::has_signature_marker` and `Reader::inspect_cached`. Inspection already reads the file once and scans `/Sig` candidates with SIMD while checking exact prefixes. Cached inspect is a separate repeated-use interface; it cannot replace cold CLI classification in the benchmark. Allocation gates report cumulative traffic, not peak RAM.
- Candidate 100: installed lopdf 0.45.0 `Document::get_pages` collects `page_iter().enumerate()` into a BTreeMap; the loader only used its length. Direct counting demonstrably removes two allocations on the text-heavy input while retaining the same iterator and its traversal limits.

The ranking is an engineering hypothesis informed by these reachable sites and the measurements below, not a promise of 100 independent speedups. Existing optimizations, alternatives, rejected experiments and unmeasured candidates are explicitly distinguished from retained, verified changes. Large startup gains have taken priority over micro-optimizations after measurements showed classification itself reporting 0–1 ms.

## Implementation evidence

- RED: `python scripts/test_classification_medal_performance.py --repeats 25` failed at 23.810 ms against the 14.389 ms target; correct pages/kind/signature output was asserted on every launch.
- Parser-startup slice (candidates 6, 8, 9): lopdf now uses its existing sequential parser by default; the `parallel-loader` feature restores parallel object parsing for batch consumers. Rayon remains available to profitable page/stream extraction. This is not fixture-specific.
- Paired evidence: 31 interleaved launches per binary measured the candidate at 17.777 ms versus the preserved parallel-parser binary at 21.047 ms (15.54% lower). Every sample remains in the tool output. Absolute medal gate still RED under external load.
- Correctness: vendor library suite 1,633/1,633 GREEN; public reader acceptance 18/18 GREEN, including classification equivalence across the eight-document corpus.
- Rejected evidence: setting `RAYON_NUM_THREADS=1` alone gave inconclusive results under varying load; it is not set by the implementation or canonical harness.
- First full 40-card, nine-repeat run completed (`benchmark-20261002T014716Z-merged.json`): 36 gold and 4 silver under varying external load. The canonical report was not replaced during this intermediate investigation.
- Routing slice (candidates 1–4): removed the redundant document-wide clear-text probe; launch routing now constructs its page map/scan plan once and uses the existing per-page proof before the exact fallback. Character-diversity counting uses three masked population counts instead of checking all 256 possible byte values.
- After the routing slice: vendor library suite 1,633/1,633 GREEN and public reader acceptance 18/18 GREEN. Changed-file rustfmt check passes; repository-wide cargo fmt hits a formatter stack overflow.
- Latest release paired check: 31 launches per binary measured 22.541 ms candidate versus 26.130 ms baseline (13.74% reduction); absolute medal gate remains RED.
- Complete verification run `benchmark-20261002T020015Z-merged.json`: all 40 workloads succeeded, with 31 gold / 7 silver / 2 bronze against unchanged competitor rows. Canonical reports now show this complete run, not a collection of historical best results.
- Startup diagnostic immediately afterward: 25 paired usage/inspect launches measured 12.381 ms for the no-document usage path and 13.655 ms for inspection; internal classification reported 0–1 ms. A subsequent formal 31-repeat gate measured 14.477 ms (RED against 14.389 ms). This variation warrants caution before attributing all medal changes to code.
- Second complete nine-repeat matrix `benchmark-20261002T020959Z-merged.json`: all 40 workloads succeeded, with 33 gold / 5 silver / 2 bronze. Both canonical reports were updated to this latest complete run, and the workload-graph test passed. Competitor measurements were unchanged.
- Remaining non-gold cards in the latest run: Markdown extraction for Financial table, Image document, and Text-heavy; classification for Image document, Multi-column, and Text-heavy; first-page text layer for Multi-column. Compared with the immediately previous complete run, two medals improved without production changes, so load variation remains significant.
- The 40-gold goal is not achieved. No claim that all 100 candidates are implemented or beneficial; alternatives and already-existing optimizations remain subject to evidence.

## Subsequent extraction slices

Recommendations 1, 3, 6 from the follow-up extraction investigation were implemented with red/green tests; see `vector-clones-scheduling.md` for changes, output equivalence, allocation traffic and paired timings. The latest complete run is `benchmark-20261002T023602Z-merged.json`: 36 gold / 4 silver, with all 40 workloads successful and canonical reports updated. Remaining silvers are financial-table Markdown, image-document Markdown, image-document classification and text-heavy classification. Competitor rows remain unchanged; the 40-gold goal remains unachieved.

## October 2 clean-loader and compact-CLI investigation

The subsequent page-borrowing build reached 37 gold / 3 silver in `benchmark-20261002T054551Z-merged.json`; see `four-silvers-followup.md`. Remaining cards are image Markdown and image/text classification. The classification gate reproduced RED at 14.4663 ms (25 samples, correct metadata) against 14.389 ms.

- Candidate 71: clean normal-xref completeness is now proven before constructing the overlong-BBox repair indexes. Missing normal objects still use the unchanged repair algorithm; missing compressed arrays still use the separate object-stream recovery. Public inspection allocation test RED at 1,154 calls against 1,150, GREEN at 1,146 (691,476 -> 690,888 bytes). All 1,636 library tests, including malformed and overlong-BBox recovery, and 18 reader acceptance tests pass.
- Follow-up extraction slice: `Tf` retains the current font-name String's storage; lossy UTF-8 decoding and assignment semantics are unchanged. Public Markdown allocation test RED at 314,505,415 bytes against 314,440,000; GREEN at 314,371,011 with identical warmed Markdown, kind and page count. Cumulative allocation traffic is not peak memory; small run-to-run variation exists.
- Candidates 12–14: dedicated `blazepdf-inspect` CLI exposes the same public Reader inspection cost tier and metadata format, allowing link-time removal of unreachable extraction/rendering code. Corpus CLI equivalence test RED on the unimplemented entry point, GREEN across all eight documents. It uses one locked stdout write. Benchmark adapter configured-executable test RED when ignored, GREEN after reusing the existing executable resolver; other BlazePDF adapters retain their defaults.
- Compact CLI rejected after 51 alternating-order paired launches: 14.6851 ms compact versus 14.6448 ms shared, still RED against 14.389 ms. Executable size fell from 7,481,856 to 2,754,048 bytes, but cold-launch latency did not. The compact entry point, its temporary test, and the adapter experiment were removed; no benchmark command was switched. The gate retains an optional candidate path for future controlled experiments.
- Retained loader/font slices: all 24 paired corpus output checks passed. Fifteen paired samples measured text Markdown 35.0724 -> 34.0182 ms; image Markdown 287.8170 -> 291.0984 ms, essentially flat/slightly slower; image first-page 219.5898 -> 217.5236 ms. Allocation savings are demonstrated; no causal image latency win is claimed.
- The completeness proof was refactored to one allocation-free merge walk over the ordered xref and loaded-object maps, avoiding per-entry logarithmic lookup. Inspection allocation gate, eight overlong-BBox repair tests and 18 reader acceptance tests remain GREEN.
- Complete nine-repeat matrix `benchmark-20261002T060609Z-merged.json`: all 40 BlazePDF rows succeeded; **37 gold / 3 silver**. Image Markdown 320.100 versus stored MuPDF 298.699 ms; image classification 26.835 versus 23.506 ms; text-heavy classification 16.537 versus 14.389 ms. Both canonical reports updated; workload graph tests passed. Competitor rows unchanged, no historical-best aggregation. The 40-gold objective remains incomplete.
- Next hypothesis check: the real text-heavy stream has 3,546 operators and no Tr/BI operators; 289 repeated q/re/W*/n/BT/Tf/Tm/g/G/TJ/ET/Q blocks. Relaxing a Tr rejection cannot help this document. Startup dominates its cold measurement; numeric/string scan work remains a candidate for the large image-label document.

This remains a ranked candidate list, not a claim of 100 implemented improvements. No fixture-specific routing, reduced scan safety, competitor-row edits, or historical-best aggregation was introduced.

## Route ignored-byte run experiment

- Reproduced the public text classification performance gate RED at 15.9837 ms over 31 launches, with correct metadata on every launch.
- The image document's first stream is 1,112,481 inflated bytes. Raw numeric/whitespace run analysis found 1,052,949 matching bytes in 51,974 runs, maximum length 46. This includes any matching bytes inside literals; the scanner still handles literal bodies separately and does not skip them with this optimization.
- Experimental scanner consumes contiguous digits, signs, decimal points and PDF whitespace together. Those bytes previously had no state changes outside names/strings/comments; each run ends before any previously observable byte. Operator/string/name handling, character diversity, route thresholds and fallback conditions remain unchanged.
- All 1,636 library tests, 18 public reader acceptance tests, and the inspection allocation gate pass. Changed-file rustfmt check passes. Preserved baseline: `target/release/blazepdf-before-route-runs.exe`.
- All 24 release corpus output checks passed. Twenty-one alternating-order pairs: image classification 26.9294 -> 26.4520 ms (1.77% lower); text classification 16.2408 -> 15.7583 ms (2.97% lower). Fourteen of 21 pairs were faster in each classification case; median paired savings 0.6835 and 0.4091 ms respectively. Image Markdown remained flat/slightly slower (314.0704 -> 317.2955 ms), not a claimed gain.
- A separate 61-pair text gate measured 14.8476 -> 14.5419 ms. The 14.389 ms absolute target remains RED; correctness stayed unchanged. Retained provisionally for the complete matrix check, not a claimed 40-gold achievement.
- Complete 40-card nine-repeat verification succeeded: `benchmark-20261002T062016Z-merged.json`, **39 gold / 1 silver**. Both image cards gained gold; the only silver is Text-heavy classification at 18.015 ms versus stored MuPDF 14.389 ms. Canonical reports updated and workload-graph test passes. No claim that both medal changes are entirely caused by the scanner patch; paired results support a modest classification improvement, while full-run external load varies.
- Next priority is candidate 94 (CRT startup), not more changes to classification rules. PE import inspection confirms VCRUNTIME140.dll plus six api-ms-win-crt imports, and the local compiler advertises crt-static support. The compact-binary experiment did not change these imports, so its negative result does not settle this hypothesis. Static-link performance/correctness still require controlled testing before any build policy change.

## Static CRT slice (candidate 94)

- Public cold-classification gate RED at 15.7118 ms over 31 launches. The import-contract check was RED on the baseline's VCRUNTIME140 and six UCRT API imports.
- Controlled initial build: `cargo rustc --release --no-default-features --bin blazepdf -- -C target-feature=+crt-static`. Import check GREEN: none of those CRT DLLs remain.
- Eighty-one alternating-order pairs: static 14.9421 ms versus dynamic 16.6508 ms (10.26% lower); static faster in 70/81 pairs, median paired saving 1.4995 ms. Absolute 14.389 ms gold gate remains RED under this load.
- All 24 classify/first-page/Markdown corpus output comparisons match. Fifteen paired samples improved all eight measured cases: image Markdown 317.218 -> 303.733 ms; text Markdown 36.2146 -> 34.6480; table Markdown 24.5132 -> 22.0967; image classification 24.8938 -> 23.5395; text classification 17.0201 -> 14.7282; columns classification 17.4711 -> 14.6810; image first-page 222.7991 -> 216.3968; columns first-page 22.2789 -> 19.6665. Samples retain substantial variation, so not every percentage is a precise causal estimate.
- Added `.cargo/config.toml`, scoped to `x86_64-pc-windows-msvc`, so normal Cargo builds apply static CRT consistently to dependencies, CLI and viewport. Other targets retain their defaults. No classifier rule or PDF safety limit changed.
- New standard-library-only `scripts/test_release_crt_imports.py` checks actual PE imports, not configuration text. RED on the old viewport artifact; complete rebuild/import GREEN check pending.
- Coherent-build verification: 1,636 library tests, 18 public acceptance tests and both resource gates GREEN. Normal Cargo CLI build also passes the standard-library-only PE import gate; viewport rebuild and full 40-card nine-repeat benchmark remain underway. Preserved dynamic artifacts: `blazepdf-before-static-crt.exe` and `blazepdf-window-before-static-crt.exe`. No new medal claim until the complete matrix finishes.
- Paired comparison helper now supports `--verify-render`, adding exact native raster-byte comparisons for all eight corpus documents to the existing 24 output checks. Temporary uniquely named PPMs are removed after each comparison. This stronger coherent-build correctness check will run after the full measurement, not compete with it for CPU.
- Complete coherent-build nine-repeat matrix `benchmark-20261002T064629Z-merged.json`: all 40 rows succeeded, **36 gold / 4 silver**. Remaining cards: table Markdown 28.355 versus stored MuPDF 28.259 ms; image Markdown 325.548 versus 298.699; image classification 24.829 versus 23.506; text classification 16.801 versus 14.389. Both canonical reports were updated to this newest complete run; workload-graph tests passed. Earlier 39-gold timings were not retained as a cherry-picked matrix.
- Import-contract test is GREEN for both normal Cargo release executables. After that matrix, coherent-build correctness comparison is GREEN for all 24 text/metadata outputs and all eight exact native raster outputs. No temporary raster artifacts remain.
- Fresh 15-pair comparison showed large changes in absolute timing for **both** builds: text classification static 28.9774 versus dynamic 33.0667 ms; image classification 39.7177 versus 47.1198. Static improved seven of eight case medians, but image Markdown was 395.4767 versus 375.8495 (5.22% slower in this sample). Earlier sample medians were 303.733 versus 317.218 respectively. This variation prevents attributing every full-matrix ranking change to compiler flags. Static CRT remains supported by the strong 81-pair startup result; the 40-gold goal remains unachieved.
- A later read-only CPU counter sampled 27.57% total CPU utilization. It was not captured during every timed launch and does not establish the cause of each outlier; no other program was stopped or reprioritized.

## Inspection output slice (candidates 13–14)

- Public classification latency gate reproduced RED at 16.3797 ms (31 launches, correct metadata) against 14.389 ms.
- Isolated the real CLI metadata formatter behind its output-sink seam. RED: complete metadata took nine sink writes, violating the one-write resource contract. The sink is an I/O-boundary test double, not a mock of Reader or the detector.
- GREEN: format the unchanged four lines once, then write_all through the locked stdout sink. All three CLI tests and 18 reader acceptance tests pass. Valid metadata bytes, including the final newline, are unchanged; I/O failures propagate from the formatter.
- Only inspect output changed; first-page, Markdown and raster formatting retain their existing paths. Preserved baseline: `target/release/blazepdf-before-inspection-write.exe`. Release paired timings and the complete matrix remain pending; no latency or medal claim yet.
- Release classification gate GREEN over 81 alternating-order pairs: candidate 13.9138 ms versus baseline 14.6773 ms, below the stored 14.389 ms gold threshold. All launches validated metadata.
- Separate 15-pair corpus comparison: all 24 metadata/text outputs and eight exact native raster outputs match. Image classification 24.6401 -> 23.4004 ms; text classification 16.6051 -> 16.3273 ms. The latter sample remains above the absolute target, illustrating timing variation. Non-inspection paths also varied despite having no implementation change; their differences are not attributed to metadata buffering. Full 40-card verification is underway.
- Complete nine-repeat matrix `benchmark-20261002T071445Z-merged.json`: all 40 workloads succeeded, **39 gold / 1 silver**. Only Text-heavy classification remains non-gold: 15.662 versus stored MuPDF 14.389 ms. Both canonical reports updated; graph test and both canonical-publication tests pass. All 176 competitor rows come from the unchanged September 30 reference. No historical-best aggregation or claim of 40 gold. The goal remains active.

## Loader page-count resource slice (candidate 3 follow-up)

- Installed lopdf 0.45.0 implements get_pages by enumerating page_iter into a BTreeMap. The loader only needed its length, while routing/extraction construct their own maps afterward.
- Public Reader inspection resource gate tightened to 1,145 allocation calls: RED at 1,146 calls / 690,888 bytes. Counting the same iterator directly is GREEN at 1,144 calls / 690,696 bytes. Traversal, iterator limits and the zero-readable-pages error remain unchanged; no raw-byte page estimation was introduced.
- All 18 public acceptance tests and 1,636 vendor library tests pass. Preserved release baseline: `target/release/blazepdf-before-page-count.exe`. Release rebuild and timing verification remain pending; this is a demonstrated allocation saving, not yet a demonstrated latency win.
- Release rebuild complete. Eighty-one alternating-order classification pairs: candidate 12.7089 versus baseline 12.9937 ms, absolute gate GREEN. All 24 text/metadata and eight exact native raster outputs match. A separate 15-pair sample measured text classification 15.5726 -> 15.1645 ms and image classification 21.1204 -> 20.1737 ms; column classification 15.4008 -> 15.5366 ms was slightly slower. Variation remains significant; full-matrix verification is next, and no new medal claim is made from the paired gate alone.

## Final verification and completion audit

- Complete release matrix `benchmark-20261002T072651Z.json`, merged into `benchmark-20261002T072651Z-merged.json`: **40 gold / 0 silver**, all 40 successful. Coverage is eight documents in each of five separate workloads; no workload classes were collapsed. Nine samples per BlazePDF row, one excluded warmup. All samples remain in the JSON.
- Independently recomputed Text-heavy classification median from all nine samples: 13.455 ms, below stored MuPDF 14.389 ms. Source samples: 12.630, 15.136, 13.413, 12.931, 11.292, 13.688, 16.429, 13.455, 13.548 ms. Timing variation remains real; 40 gold is the observed latest-run result, not a claim that every launch wins or that the last two allocations alone caused the complete improvement.
- Raw, merged and canonical BlazePDF rows match exactly when compared by workload/document key. All 176 competitor rows are unchanged from the September 30 reference. The only failed initial audit assertion compared randomized raw-row order with merged-row order; keyed comparison passed with no row-content differences.
- Both canonical HTML reports regenerated from the newest complete merged run. Parsed embedded graph data confirms 40 benchmark cards and BlazePDF rank 1 in every card. No selective probe or historical-best card set was published.
- Final-build correctness: all 24 text/metadata output comparisons and eight exact native raster-byte comparisons match the preserved pre-page-count baseline. Post-publication Rust check: three CLI tests, 18 reader acceptance tests and both allocation gates pass. Inspection is 1,144 calls / 690,696 bytes; vector-heavy Markdown is 314,370,815 cumulative allocated bytes. The current loader change also passed all 1,636 vendor library tests before release build; no Rust source changed afterward.
- Both current release executables pass PE import-contract checks (no dynamic CRT imports). Parsing, decompression and traversal bounds, conservative classification fallbacks, zero-readable-pages errors and signature-prefix validation remain in place. No fixture-specific route, competitor edits, sample suppression or interference with unrelated programs was introduced.
- Report metadata audit found that merged reports displayed the base run's five repeats as if uniform. TDD: mixed five-/nine-sample render test RED, then GREEN after both reports derive their label from actual successful-row samples. Current reports correctly say "5 to 9 measured runs per case (mixed sample counts)"; preserved competitor rows include five and six samples, BlazePDF rows nine. This changes labels only, not times or ranks. Uniform, legacy, failed-row exclusion and no-success metadata checks also pass, along with workload-graph and both canonical-selection tests.
- The list contains exactly 100 ranked optimization candidates with source anchors and evidence limits. Retained implementation slices have red/green and paired/correctness evidence above; already-present behavior, rejected alternatives and unmeasured candidates are not claimed as 100 separate implemented wins. The requested 40-gold terminal result is verified; no additional optimization is needed to reach that result.
