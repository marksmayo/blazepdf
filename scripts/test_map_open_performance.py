"""Manual release-mode output regression and timing probe for the dense map.

Run after `cargo build --release --no-default-features --bin blazepdf`.
Timing is reported, not asserted: host load makes a fixed latency bound flaky.
"""

from pathlib import Path
import hashlib
import re
import statistics
import subprocess


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "target" / "release" / "blazepdf.exe"
FIXTURE = ROOT / "vendors" / "CalyPdf" / "Caly.Benchmarks" / "fseprd1102849.pdf"
MARKDOWN_SHA256 = "3b74eb2decec9f8ff292c180277d51c75e88191470230b59b28dee66b647d9d3"


def main() -> None:
    times = []
    for _ in range(4):
        run = subprocess.run([str(EXE), str(FIXTURE)], capture_output=True, check=True)
        output = run.stdout.decode("utf-8")
        assert "kind: Text" in output
        assert "PURPOSE AND CONTENTS" in output
        assert "National Forest" in output
        markdown = run.stdout.split(b"\n\n", 1)[1]
        assert hashlib.sha256(markdown).hexdigest() == MARKDOWN_SHA256
        times.append(int(re.search(r"processed: (\d+) ms", output).group(1)))

    median = statistics.median(times[1:])
    print(f"dense map open: median {median:.0f} ms, samples {times[1:]}")


if __name__ == "__main__":
    main()
