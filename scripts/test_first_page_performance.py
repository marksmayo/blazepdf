"""Manual first-page output regression and timing probe for the dense map."""

from pathlib import Path
import hashlib
import statistics
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "target" / "release" / "blazepdf.exe"
FIXTURE = ROOT / "vendors" / "CalyPdf" / "Caly.Benchmarks" / "fseprd1102849.pdf"
EXPECTED_SHA256 = "fad0fb5d268249a5b3cfaa212f3f8ddc9fd8f23952d443a1e280c7c25378d6f2"


def main() -> None:
    times = []
    for _ in range(5):
        started = time.perf_counter()
        run = subprocess.run([str(EXE), "--first-page", str(FIXTURE)], capture_output=True, check=True)
        times.append((time.perf_counter() - started) * 1000)
        assert hashlib.sha256(run.stdout).hexdigest() == EXPECTED_SHA256

    median = statistics.median(times[1:])
    print(f"dense map first page: median {median:.0f} ms, samples {[round(t) for t in times[1:]]}")


if __name__ == "__main__":
    main()
