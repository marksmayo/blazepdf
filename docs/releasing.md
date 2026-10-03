# Release process

No release is created automatically by CI. A maintainer must explicitly approve
and publish each release; this guide does not publish one.

1. Choose a version and update `Cargo.toml` and `Cargo.lock` consistently. Move
   relevant Unreleased changelog entries into a dated version section.
2. Run the checks in CONTRIBUTING.md on a clean checkout and require green CI.
   Test the default desktop build separately if shipping the viewport.
3. Build Windows release binaries with `cargo build --release --locked`. Exercise
   inspection, text extraction and error handling; verify any shipped rendering
   capability using the intended PDFium runtime. Preserve output evidence.
4. Package only verified binaries with LICENSE, NOTICE and runtime/setup guidance.
   Do not bundle third-party PDFs or runtimes without checking redistribution
   terms. Generate SHA-256 checksums for every downloadable asset.
5. After approval, create a version tag matching Cargo's version and a GitHub
   release with changelog, platform/toolchain details, checksums and known limits.
   Mark experimental releases as prereleases where appropriate.
6. Verify downloads from the published release. The README release badge then
   links to the latest eligible release; prerelease-only publication may not appear.

Benchmark claims must retain dates, sample counts and competitor provenance. A new
binary release does not automatically inherit the old binary's timings. Never
upload secrets, private source documents or unrelated local build outputs.
