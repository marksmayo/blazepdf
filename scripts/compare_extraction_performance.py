"""Paired cold-launch measurements with before/after output equivalence."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def normalized(output):
    header, separator, body = output.partition(b"\n\n")
    header = b"\n".join(
        line for line in header.splitlines() if not line.startswith(b"processed: ")
    )
    return header + separator + body


def launch(executable, mode, path):
    started = time.perf_counter_ns()
    result = subprocess.run(
        [str(executable), *mode, str(path)], capture_output=True, check=True
    )
    return (time.perf_counter_ns() - started) / 1e6, normalized(result.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--baseline", type=Path, default=ROOT / "target/release/blazepdf-before-vector-clones-scheduling.exe")
    parser.add_argument("--verify-render", action="store_true", help="also compare exact native raster bytes across the corpus")
    args = parser.parse_args()
    assert args.repeats > 0
    binaries = {"baseline": args.baseline.resolve(), "candidate": ROOT / "target/release/blazepdf.exe"}
    corpus = json.loads((ROOT / "benchmarks/corpus.json").read_text(encoding="utf-8"))["documents"]
    documents = {doc["id"]: ROOT / doc["path"] for doc in corpus}
    render_checks = 0
    if args.verify_render:
        artifacts = ROOT / "target/benchmark-artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        run_id = uuid.uuid4().hex
        for index, doc in enumerate(corpus):
            outputs = []
            digests = []
            try:
                for name, executable in binaries.items():
                    output = artifacts / f"render-diff-{run_id}-{index}-{name}.ppm"
                    assert not output.exists(), output
                    outputs.append(output)
                    subprocess.run([str(executable), "--render", str(documents[doc["id"]]), str(output)], capture_output=True, check=True)
                    data = output.read_bytes()
                    assert data.startswith(b"P6\n"), f"invalid raster: {name}/{doc['id']}"
                    digests.append(hashlib.sha256(data).digest())
                assert digests[0] == digests[1], f"native raster changed: {doc['id']}"
                render_checks += 1
            finally:
                for output in outputs:
                    output.unlink(missing_ok=True)
    # Correctness covers the entire corpus, not just the cards being optimized.
    modes = {"classify": ["--inspect"], "first-page": ["--first-page"], "markdown": []}
    expected = {}
    for doc in corpus:
        for work, mode in modes.items():
            _, before = launch(binaries["baseline"], mode, documents[doc["id"]])
            _, after = launch(binaries["candidate"], mode, documents[doc["id"]])
            assert before == after, f"output changed: {work}/{doc['id']}"
            expected[(work, doc["id"])] = before
    cases = [("markdown", doc) for doc in ("image", "text", "table")]
    cases += [("classify", doc) for doc in ("image", "text", "columns")]
    cases += [("first-page", doc) for doc in ("image", "columns")]
    report = {}
    for work, doc in cases:
        samples = {name: [] for name in binaries}
        for index in range(args.repeats):
            names = list(binaries)
            if index % 2:
                names.reverse()
            for name in names:
                elapsed, output = launch(binaries[name], modes[work], documents[doc])
                assert output == expected[(work, doc)], f"unstable output: {name}/{work}/{doc}"
                samples[name].append(elapsed)
        medians = {name: statistics.median(values) for name, values in samples.items()}
        report[f"{work}/{doc}"] = {
            "samples_ms": samples, "medians_ms": medians,
            "improvement_percent": 100 * (1 - medians["candidate"] / medians["baseline"]),
        }
    print(json.dumps({"corpus_output_checks": len(expected), "native_render_output_checks": render_checks, "repeats": args.repeats, "cases": report}, indent=2))


if __name__ == "__main__":
    main()
