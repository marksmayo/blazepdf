# Third-party notices and benchmark provenance

The root MIT license covers BlazePDF's own code. Third-party source and assets
retain their original notices and licenses.

`crates/pdf-inspector` is an ordinary source snapshot, not a submodule. It derives
from [firecrawl/pdf-inspector](https://github.com/firecrawl/pdf-inspector) at commit
`876fe9ac65c1b05512b9a1a182b5c56bcfdd6c39`, including local correctness and performance
changes. Firecrawl's MIT notice remains in [its LICENSE](crates/pdf-inspector/LICENSE).
Bundled Adobe CMaps retain [their notice](crates/pdf-inspector/external/bcmaps/LICENSE).
Cargo dependencies retain their own licenses; versions are pinned in Cargo.lock.
PDFium is separately supplied and is not bundled here.

Third-party PDFs are not redistributed. The optional corpus bootstrap downloads
only eight commit-pinned files and verifies SHA-256 hashes. Review upstream notices
and document terms before reuse. Sources and revisions:

- [CalyPdf/CalyPdf](https://github.com/CalyPdf/CalyPdf): `2a365a9b348a05994c215f7dd3b66ccdd4c22cd0`.
- [firecrawl/pdf-inspector](https://github.com/firecrawl/pdf-inspector): `876fe9ac65c1b05512b9a1a182b5c56bcfdd6c39`.
- [sumatrapdfreader/sumatrapdf](https://github.com/sumatrapdfreader/sumatrapdf): `46a79eb59c949a9b7a4c4d2b701b82a07a0c9730`.

Other readers are external installations, not software distributed with BlazePDF.
Product names identify measurements, not affiliation or endorsement.

Benchmark JSON retains original commands, machine details and local paths as
evidence; those paths are not portable setup instructions. BlazePDF's measurements
are from 2 October 2026, while competitors retain the 30 September reference.
This is not a simultaneous all-product rerun.
