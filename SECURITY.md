# Security policy

BlazePDF is experimental. PDF parsing and native rendering process potentially
hostile input; do not treat the viewer as a security sandbox. Avoid opening
untrusted PDFs outside a suitably isolated environment. Keep PDFium and other
runtime dependencies updated independently.

## Reporting

Do not put exploit PDFs, secrets or vulnerability details in a public issue.
Use [GitHub's private Report a vulnerability form](https://github.com/marksmayo/blazepdf/security/advisories/new).
Private reporting is enabled for this repository. If the form is unavailable,
open a minimal issue asking the
maintainer to enable private vulnerability reporting, without technical details
or attachments, and wait for a private channel before sharing them.

Include the affected revision, platform, dependency versions, minimal reproduction,
impact and whether native PDFium is involved. Share only files you have permission
to disclose. A minimal synthetic reproducer is preferable to a confidential PDF.

## Maintenance scope

Reports against current `main` are welcome. There are no declared supported stable
release branches or guaranteed response times yet. Signature markers are not
cryptographic validation; benchmark wins are not evidence of security.
