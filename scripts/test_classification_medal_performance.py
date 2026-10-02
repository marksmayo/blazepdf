"""Cold-process inspection gate; retains all samples and checks real CLI output."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf"
LIMIT_MS = 14.389


def inspect(executable):
    started = time.perf_counter_ns()
    result = subprocess.run(
        [str(executable), "--inspect", str(FIXTURE)], capture_output=True, check=True
    )
    elapsed = (time.perf_counter_ns() - started) / 1e6
    lines = result.stdout.decode("utf-8").splitlines()
    assert lines[:3] == ["pages: 1", "kind: Text", "signed: false"], lines
    assert len(lines) == 4 and lines[3].startswith("processed: "), lines
    return elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path, default=ROOT / "target/release/blazepdf.exe")
    parser.add_argument("--repeats", type=int, default=25)
    args = parser.parse_args()
    executables = {"candidate": args.candidate.resolve()}
    if args.baseline:
        executables["baseline"] = args.baseline.resolve()
    samples = {name: [] for name in executables}
    for executable in executables.values():
        inspect(executable)  # excluded warm-up
    for index in range(args.repeats):
        names = list(executables)
        if index % 2:
            names.reverse()
        for name in names:
            samples[name].append(inspect(executables[name]))
    medians = {name: statistics.median(values) for name, values in samples.items()}
    print(json.dumps({"samples_ms": samples, "medians_ms": medians}, indent=2))
    assert medians["candidate"] < LIMIT_MS, (
        f"Text-heavy inspection {medians['candidate']:.3f} ms >= {LIMIT_MS:.3f} ms"
    )


if __name__ == "__main__":
    main()
