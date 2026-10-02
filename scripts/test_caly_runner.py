"""Acceptance checks for CalyPdf benchmark workload modes."""

import json
import subprocess

from benchmark import ROOT


def run_mode(mode: str) -> dict:
    runner = ROOT / "benchmarks/adapters/CalyRunner/bin/Release/net10.0/CalyRunner.dll"
    pdf = ROOT / "vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf"
    result = subprocess.run(
        ["dotnet", str(runner), mode, str(pdf)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def main() -> None:
    inspection = run_mode("--inspect")
    assert inspection["pages"] > 0
    assert inspection["mode"] == "inspect"

    markdown = run_mode("--markdown")
    assert markdown["mode"] == "markdown"
    assert markdown["markdown_chars"] > 100


if __name__ == "__main__":
    main()
