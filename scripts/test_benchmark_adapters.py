"""Regression checks for native benchmark adapter command construction."""

from pathlib import Path
import json

from benchmark import ROOT, command, document_window_title, is_new_document_window, stats


def main() -> None:
    pdf = ROOT / "vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf"
    readers = json.loads((ROOT / "benchmarks" / "readers.json").read_text(encoding="utf-8"))["readers"]
    reader = {
        "id": "sumatrapdf-first-page",
        "adapter": "sumatra-tool-text",
        "executable": "vendors/sumatrapdf-tool/extracted/sumatrapdf-tool.exe",
    }
    cmd, reason = command(reader, pdf)
    assert reason is None
    assert cmd is not None
    assert cmd[1:4] == ["convert", "-o", str(ROOT / "target/benchmark-artifacts/sumatrapdf-first-page-2559 words.txt")]
    assert cmd[4:7] == ["-F", "text", str(pdf)]
    assert cmd[-1] == "1"

    metadata_reader = {
        "id": "sumatrapdf-metadata",
        "adapter": "sumatra-tool-pages",
        "executable": "vendors/sumatrapdf-tool/extracted/sumatrapdf-tool.exe",
    }
    metadata_cmd, reason = command(metadata_reader, pdf)
    assert reason is None
    assert metadata_cmd == [str(ROOT / metadata_reader["executable"]), "pages", str(pdf), "1"]

    mutool = ROOT / "scripts" / "benchmark.py"  # Existing path is enough to test command construction.
    mupdf = {"id": "mupdf-first-page", "adapter": "mutool-text", "executable": str(mutool)}
    text_cmd, reason = command(mupdf, pdf)
    assert reason is None
    assert text_cmd == [str(mutool), "draw", "-q", "-F", "text", str(pdf), "1"]

    mupdf_render = {"id": "mupdf-render", "adapter": "mutool-render", "executable": str(mutool)}
    render_cmd, reason = command(mupdf_render, pdf)
    assert reason is None
    assert render_cmd == [str(mutool), "draw", "-q", "-r", "150", "-o", str(ROOT / "target/benchmark-artifacts/mupdf-render-2559 words.png"), str(pdf), "1"]

    mupdf_info = {"id": "mupdf-info", "adapter": "mutool-info", "executable": str(mutool)}
    info_cmd, reason = command(mupdf_info, pdf)
    assert reason is None
    assert info_cmd == [str(mutool), "info", str(pdf)]

    blaze_render = {"id": "blazepdf-render", "adapter": "blazepdf-render"}
    blaze_cmd, reason = command(blaze_render, pdf)
    assert reason is None
    assert blaze_cmd[1] == "--render"
    assert blaze_cmd[2] == str(pdf)
    assert blaze_cmd[3].endswith("blazepdf-render-2559 words.ppm")

    blaze_window = next(reader for reader in readers if reader["id"] == "blazepdf-window")
    window_cmd, reason = command(blaze_window, pdf)
    assert reason is None
    assert blaze_window["adapter"] == "window-ready-signal"
    assert blaze_window["ready_signal"] == "BLAZEPDF_FIRST_FRAME_READY"
    assert blaze_window["environment"]["BLAZEPDF_BENCHMARK_SHELL_ONLY"] == "1"
    assert window_cmd[-1] == str(pdf)

    distribution = stats([1.0, 2.0, 3.0, 4.0, 5.0])
    assert distribution["p10_ms"] == 1.0
    assert distribution["p90_ms"] == 5.0

    sioyek = {
        "id": "sioyek-window",
        "adapter": "window-ready",
        "executable": "C:/Users/markm/AppData/Local/Microsoft/WinGet/Packages/ahrm.sioyek_Microsoft.Winget.Source_8wekyb3d8bbwe/sioyek-release-windows/sioyek.exe",
    }
    sioyek_cmd, reason = command(sioyek, pdf)
    assert reason is None
    assert sioyek_cmd == [str(ROOT / sioyek["executable"]), str(ROOT / pdf)]

    edge = next(reader for reader in readers if reader["id"] == "edge-pdf-window")
    edge_cmd, reason = command(edge, pdf)
    assert reason is None
    assert edge_cmd == [str(ROOT / edge["executable"]), *edge["args"], str(ROOT / pdf)]
    assert "--user-data-dir=" in edge["args"][1]
    assert document_window_title("2559 words.pdf - Google Chrome", pdf)
    assert document_window_title("Untitled and 1 more page - Profile 1 - Microsoft\u200b Edge", pdf, None, "Microsoft Edge")
    assert not document_window_title("New Tab - Google Chrome", pdf)
    signed_pdf = ROOT / "vendors/sumatrapdf/tests/issue-5581-data/test_sign_PAdES_B-LTA.pdf"
    assert document_window_title("Test Document - PDF-XChange Editor", signed_pdf, "Test Document")
    assert is_new_document_window(42, "Test Document - WPS Office", {41}, signed_pdf, "Test Document")
    assert not is_new_document_window(41, "Test Document - WPS Office", {41}, signed_pdf, "Test Document")
    assert is_new_document_window(41, "2559 words.pdf - Microsoft Edge", {41}, pdf, allow_foreign_pid=True)
    assert not is_new_document_window(42, "New Tab - Google Chrome", {41}, signed_pdf, "Test Document")

    sejda = next(reader for reader in readers if reader["id"] == "sejda-window")
    sejda_cmd, reason = command(sejda, pdf)
    assert reason is None
    assert sejda_cmd == [str(ROOT / sejda["executable"]), str(ROOT / pdf)]

    wps = next(reader for reader in readers if reader["id"] == "wps-pdf-window")
    wps_cmd, reason = command(wps, pdf)
    assert reason is None
    # wps.exe is only a launcher: it hands the document to a preloaded wpspdf
    # process and exits 0, so no new visible window is ever attributed to it.
    # The PDF component must be launched directly to be measurable.
    assert Path(wps["executable"]).name == "wpspdf.exe"
    assert "args" not in wps
    assert wps_cmd == [str(ROOT / wps["executable"]), str(ROOT / pdf)]

    updf = next(reader for reader in readers if reader["id"] == "updf-window")
    updf_cmd, reason = command(updf, pdf)
    assert reason is None
    assert updf_cmd == [str(ROOT / updf["executable"]), str(ROOT / pdf)]

    # Slim PDF Reader titles its window identically with and without a document,
    # so it matches on a reader-level title and must not claim document timing.
    slim = next(reader for reader in readers if reader["id"] == "slim-pdf-window")
    assert slim["window_title"] == "Slim PDF Reader"
    assert "document window" not in slim["work"]
    assert document_window_title("Slim PDF Reader", pdf, None, slim["window_title"])
    assert not document_window_title("Slim PDF Reader", pdf, None)


if __name__ == "__main__":
    main()
