use blazepdf::{first_page_requires_raster, DocumentKind, Reader};

#[test]
fn opens_a_text_pdf_with_renderable_text_and_markdown() {
    let document = Reader::open("vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf").unwrap();

    assert!(document.page_count > 0);
    assert_eq!(document.kind, DocumentKind::Text);
    assert!(!document.first_page_text.trim().is_empty());
    assert!(!document.markdown.trim().is_empty());
}

#[test]
fn memory_entry_points_match_path_entry_points_and_cached_reads() {
    let fixture = "vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf";
    let bytes = std::fs::read(fixture).unwrap();

    let from_bytes = Reader::open_bytes(&bytes).unwrap();
    let from_path = Reader::open(fixture).unwrap();
    assert_eq!(from_bytes.page_count, from_path.page_count);
    assert_eq!(from_bytes.kind, from_path.kind);
    assert_eq!(from_bytes.markdown, from_path.markdown);

    let reader = Reader::with_first_page_cache_capacity(1);
    let first = reader.first_page_cached(fixture).unwrap();
    let second = reader.first_page_cached(fixture).unwrap();
    assert_eq!(first.text, second.text);
    assert_eq!(reader.cache_stats().first_page_hits, 1);
    assert_eq!(
        reader.open_cached(fixture).unwrap().page_count,
        from_path.page_count
    );
}

#[test]
fn fast_open_classifies_without_building_markdown() {
    let document = Reader::inspect("vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf").unwrap();

    assert!(document.page_count > 0);
    assert_eq!(document.kind, DocumentKind::Text);
    assert!(document.processing_time_ms < 500);
}

#[test]
fn launch_routing_preserves_the_full_detector_classification_for_image_documents() {
    let fixture = "vendors/CalyPdf/Caly.Benchmarks/fseprd1102849.pdf";
    let bytes = std::fs::read(fixture).unwrap();
    let config = pdf_inspector::DetectionConfig {
        strategy: pdf_inspector::ScanStrategy::Sample(3),
        ..pdf_inspector::DetectionConfig::default()
    };

    let routing =
        pdf_inspector::detect_pdf_routing_mem_with_config(&bytes, config.clone()).unwrap();
    let detailed = pdf_inspector::detect_pdf_type_mem_with_config(&bytes, config).unwrap();

    assert_eq!(routing.pdf_type, detailed.pdf_type);
    assert_eq!(routing.page_count, detailed.page_count);
}

#[test]
fn launch_routing_matches_full_detection_across_the_benchmark_corpus() {
    let fixtures = [
        "vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf",
        "vendors/CalyPdf/Caly.Benchmarks/fseprd1102849.pdf",
        "vendors/CalyPdf/Caly.Benchmarks/Document-PublisherError-1.pdf",
        "vendors/pdf-inspector/tests/fixtures/forecast_table_chart.pdf",
        "vendors/pdf-inspector/tests/fixtures/government_positions_women.pdf",
        "vendors/pdf-inspector/tests/fixtures/rtl_hebrew_visual_words.pdf",
        "vendors/sumatrapdf/tests/issue-4839-data/rotated.pdf",
        "vendors/sumatrapdf/tests/issue-5581-data/test_sign_PAdES_B-LTA.pdf",
    ];
    let config = pdf_inspector::DetectionConfig {
        strategy: pdf_inspector::ScanStrategy::Sample(3),
        ..pdf_inspector::DetectionConfig::default()
    };

    for fixture in fixtures {
        let bytes = std::fs::read(fixture).unwrap();
        let routing =
            pdf_inspector::detect_pdf_routing_mem_with_config(&bytes, config.clone()).unwrap();
        let detailed =
            pdf_inspector::detect_pdf_type_mem_with_config(&bytes, config.clone()).unwrap();

        assert_eq!(routing.pdf_type, detailed.pdf_type, "{fixture}");
        assert_eq!(routing.page_count, detailed.page_count, "{fixture}");
    }
}

#[test]
fn renders_first_page_text_without_extracting_full_document_markdown() {
    let page = Reader::first_page("vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf").unwrap();

    assert_eq!(page.page_number, 1);
    assert!(!page.text.trim().is_empty());
}

#[test]
fn first_page_text_and_detection_share_one_reader_path() {
    let page = Reader::first_page("vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf").unwrap();

    assert_eq!(page.page_number, 1);
    assert!(!page.text.trim().is_empty());
    assert!(!page.requires_raster);
}

#[test]
fn pdf_inspector_can_classify_and_extract_the_first_page_in_one_pass() {
    let result =
        pdf_inspector::process_first_page("vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf")
            .unwrap();

    assert_eq!(result.pdf_type, pdf_inspector::PdfType::TextBased);
    assert!(!result.items.is_empty());
}

#[test]
fn page_scoped_first_page_detection_does_not_scan_other_pages_for_ocr() {
    let result =
        pdf_inspector::process_first_page("vendors/CalyPdf/Caly.Benchmarks/fseprd1102849.pdf")
            .unwrap();

    assert!(result.pages_needing_ocr.iter().all(|page| *page == 1));
    assert!(result.items.iter().all(|item| item.page == 1));
}

#[test]
fn first_page_reports_content_rotation_for_the_renderer() {
    let document =
        Reader::first_page("vendors/sumatrapdf/tests/issue-4839-data/rotated.pdf").unwrap();

    assert!(document.has_rotation);
}

#[test]
fn fast_inspection_identifies_signed_documents_for_the_trust_ui() {
    let document =
        Reader::inspect("vendors/sumatrapdf/tests/issue-5581-data/test_sign_PAdES_B-LTA.pdf")
            .unwrap();

    assert!(document.has_signature);
}

#[test]
fn interactive_reader_reuses_a_cached_first_page_text_layer() {
    let reader = Reader::new();
    let fixture = "vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf";

    let first = reader.first_page_cached(fixture).unwrap();
    let second = reader.first_page_cached(fixture).unwrap();

    assert_eq!(first.text, second.text);
    assert_eq!(reader.cache_stats().first_page_hits, 1);
}

#[test]
fn interactive_reader_evicts_the_least_recent_first_page_at_its_memory_budget() {
    let reader = Reader::with_first_page_cache_capacity(1);
    let text = "vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf";
    let rotated = "vendors/sumatrapdf/tests/issue-4839-data/rotated.pdf";

    reader.first_page_cached(text).unwrap();
    reader.first_page_cached(rotated).unwrap();
    reader.first_page_cached(text).unwrap();

    let stats = reader.cache_stats();
    assert_eq!(stats.first_page_hits, 0);
    assert_eq!(stats.cached_first_pages, 1);
}

#[test]
fn image_or_ocr_first_pages_route_to_raster_without_text_extraction() {
    assert!(first_page_requires_raster(DocumentKind::Image, false));
    assert!(first_page_requires_raster(DocumentKind::Text, true));
    assert!(!first_page_requires_raster(DocumentKind::Text, false));
}

#[test]
fn desktop_viewport_opens_a_renderable_first_page_without_markdown() {
    let viewport = Reader::open_viewport("vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf").unwrap();

    assert_eq!(viewport.title, "2559 words.pdf");
    assert!(!viewport.page.text.trim().is_empty());
    assert!(!viewport.page.requires_raster);
}

#[test]
fn interactive_viewport_reuses_the_first_page_cache() {
    let reader = Reader::new();
    let fixture = "vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf";

    let first = reader.open_viewport_cached(fixture).unwrap();
    let second = reader.open_viewport_cached(fixture).unwrap();

    assert_eq!(first.page.text, second.page.text);
    assert_eq!(reader.cache_stats().first_page_hits, 1);
}

#[test]
fn interactive_inspection_reuses_classification_and_signature_metadata() {
    let reader = Reader::new();
    let fixture = "vendors/sumatrapdf/tests/issue-5581-data/test_sign_PAdES_B-LTA.pdf";

    let first = reader.inspect_cached(fixture).unwrap();
    let second = reader.inspect_cached(fixture).unwrap();

    assert_eq!(first.page_count, second.page_count);
    assert_eq!(first.kind, second.kind);
    assert_eq!(first.has_signature, second.has_signature);
}

#[test]
fn native_renderer_returns_a_first_page_bitmap() {
    let page = Reader::render_first_page("vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf")
        .expect("PDFium runtime must be installed for the native render contract");

    assert_eq!(page.page(), 1);
    assert!(page.width() > 0);
    assert!(page.height() > 0);
    assert_eq!(
        page.format(),
        pdf_inspector::vision::RenderPixelFormat::Rgb8
    );
    assert_eq!(page.pixels().len(), page.stride() * page.height() as usize);
}
