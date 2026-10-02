"""Release-mode acceptance loop for the three remaining benchmark medals.

Build `blazepdf` in release mode first.  Each public CLI path gets one warm-up
and three measured runs.  The limits are the winning medians in the canonical
workload report, so this test stays red until BlazePDF can actually take each
card without changing its observable output.
"""

from pathlib import Path
import hashlib
import statistics
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "target" / "release" / "blazepdf.exe"
FIXTURE = ROOT / "vendors" / "CalyPdf" / "Caly.Benchmarks" / "fseprd1102849.pdf"
MARKDOWN_SHA256 = "3b74eb2decec9f8ff292c180277d51c75e88191470230b59b28dee66b647d9d3"
FIRST_PAGE_SHA256 = "fad0fb5d268249a5b3cfaa212f3f8ddc9fd8f23952d443a1e280c7c25378d6f2"

# Current winning medians in benchmark-workload-graphs.html.
LIMITS_MS = {
    "classify": 23.51,
    "first-page": 259.72,
    "markdown": 298.70,
}


def measure(arguments: list[str], validate) -> tuple[float, list[float]]:
    samples = []
    for _ in range(4):
        started = time.perf_counter()
        run = subprocess.run(
            [str(EXE), *arguments, str(FIXTURE)], capture_output=True, check=True
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        validate(run.stdout)
        samples.append(elapsed_ms)
    measured = samples[1:]
    return statistics.median(measured), measured


def validate_inspection(output: bytes) -> None:
    text = output.decode("utf-8")
    assert "pages: 2" in text
    assert "kind: Text" in text
    assert "signed: false" in text


def validate_first_page(output: bytes) -> None:
    assert hashlib.sha256(output).hexdigest() == FIRST_PAGE_SHA256


def validate_markdown(output: bytes) -> None:
    text = output.decode("utf-8")
    assert "kind: Text" in text
    assert "PURPOSE AND CONTENTS" in text
    assert "National Forest" in text
    markdown = output.split(b"\n\n", 1)[1]
    assert hashlib.sha256(markdown).hexdigest() == MARKDOWN_SHA256


def main() -> None:
    cases = (
        ("classify", ["--inspect"], validate_inspection),
        ("first-page", ["--first-page"], validate_first_page),
        ("markdown", [], validate_markdown),
    )
    failures = []
    for name, arguments, validate in cases:
        median, samples = measure(arguments, validate)
        print(f"{name}: median {median:.2f} ms; samples {[round(x, 2) for x in samples]}")
        if median >= LIMITS_MS[name]:
            failures.append(f"{name} {median:.2f} >= {LIMITS_MS[name]:.2f} ms")
    assert not failures, "medal targets missed: " + "; ".join(failures)


if __name__ == "__main__":
    main()
