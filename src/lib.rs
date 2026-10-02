//! Cross-platform BlazePDF reader core.
//!
//! The public seam is `Reader::open`: callers receive a render-ready first
//! page text layer, document classification, and semantic Markdown without
//! learning the parser's internal pipeline.

use pdf_inspector::vision::{PdfiumRenderer, RenderOptions, RenderedPage};
use pdf_inspector::{
    detect_pdf_routing_mem_with_config, process_first_page_mem, process_pdf_mem, DetectionConfig,
    PdfType, ScanStrategy,
};
use std::{
    collections::{HashMap, VecDeque},
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicUsize, Ordering},
        Mutex, OnceLock,
    },
};

/// Markdown cleanup setup is process-wide. The first full document open may
/// overlap it with parsing; later opens must not create redundant detached
/// threads after that setup has already been requested.
static MARKDOWN_WARMUP_STARTED: OnceLock<()> = OnceLock::new();

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DocumentKind {
    Text,
    Image,
    Mixed,
}

#[derive(Debug, Clone)]
pub struct Document {
    pub page_count: u32,
    pub kind: DocumentKind,
    pub first_page_text: String,
    pub markdown: String,
    pub processing_time_ms: u64,
}

#[derive(Debug, Clone)]
pub struct DocumentInspection {
    pub page_count: u32,
    pub kind: DocumentKind,
    /// True when a PDF signature field or signature dictionary marker exists.
    /// This is routing metadata, not cryptographic signature validation.
    pub has_signature: bool,
    pub processing_time_ms: u64,
}

#[derive(Debug, Clone)]
pub struct PageTextLayer {
    pub page_number: u32,
    pub text: String,
    pub has_rotation: bool,
    /// The viewport should use the raster path because no text layer exists.
    pub requires_raster: bool,
}

/// All data a native viewport needs for its first, non-blocking paint.
#[derive(Debug, Clone)]
pub struct DesktopViewport {
    pub title: String,
    pub page: PageTextLayer,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CacheStats {
    pub first_page_hits: usize,
    pub cached_first_pages: usize,
}

struct FirstPageCache {
    pages: HashMap<PathBuf, PageTextLayer>,
    least_to_most_recent: VecDeque<PathBuf>,
}

struct CachedInspection {
    file_size: u64,
    modified: Option<std::time::SystemTime>,
    value: DocumentInspection,
}

struct CachedBytes {
    file_size: u64,
    modified: Option<std::time::SystemTime>,
    bytes: std::sync::Arc<[u8]>,
}

struct CachedDocument {
    file_size: u64,
    modified: Option<std::time::SystemTime>,
    value: Document,
}

/// Stateful interactive reader services. The static methods are kept for
/// one-shot CLI and batch workloads; construct this type for page navigation.
pub struct Reader {
    first_page_cache: Mutex<FirstPageCache>,
    inspection_cache: Mutex<HashMap<PathBuf, CachedInspection>>,
    bytes_cache: Mutex<HashMap<PathBuf, CachedBytes>>,
    document_cache: Mutex<HashMap<PathBuf, CachedDocument>>,
    first_page_cache_capacity: usize,
    first_page_hits: AtomicUsize,
}

impl Default for Reader {
    fn default() -> Self {
        Self::new()
    }
}

impl Reader {
    pub fn new() -> Self {
        Self::with_first_page_cache_capacity(8)
    }

    /// Creates an interactive reader with a bounded LRU cache. A capacity of
    /// zero disables caching for memory-constrained hosts.
    pub fn with_first_page_cache_capacity(first_page_cache_capacity: usize) -> Self {
        Self {
            first_page_cache: Mutex::new(FirstPageCache {
                pages: HashMap::new(),
                least_to_most_recent: VecDeque::new(),
            }),
            inspection_cache: Mutex::new(HashMap::new()),
            bytes_cache: Mutex::new(HashMap::new()),
            document_cache: Mutex::new(HashMap::new()),
            first_page_cache_capacity,
            first_page_hits: AtomicUsize::new(0),
        }
    }

    /// Returns a cached initial text layer when the same immutable document is
    /// revisited during this reader session.
    pub fn first_page_cached(
        &self,
        path: impl AsRef<Path>,
    ) -> Result<PageTextLayer, Box<dyn std::error::Error>> {
        let path = path.as_ref();
        let key = path.to_path_buf();
        let mut cache = self
            .first_page_cache
            .lock()
            .map_err(|_| std::io::Error::other("first-page cache lock poisoned"))?;
        if let Some(page) = cache.pages.get(&key).cloned() {
            if let Some(position) = cache
                .least_to_most_recent
                .iter()
                .position(|cached| cached == &key)
            {
                cache.least_to_most_recent.remove(position);
            }
            cache.least_to_most_recent.push_back(key);
            self.first_page_hits.fetch_add(1, Ordering::Relaxed);
            return Ok(page);
        }
        drop(cache);

        let bytes = self.read_bytes_cached(path)?;
        let page = Self::first_page_bytes(&bytes)?;
        let mut cache = self
            .first_page_cache
            .lock()
            .map_err(|_| std::io::Error::other("first-page cache lock poisoned"))?;
        if self.first_page_cache_capacity > 0 {
            while cache.pages.len() >= self.first_page_cache_capacity {
                if let Some(evicted) = cache.least_to_most_recent.pop_front() {
                    cache.pages.remove(&evicted);
                } else {
                    break;
                }
            }
            cache.least_to_most_recent.push_back(key.clone());
            cache.pages.insert(key, page.clone());
        }
        Ok(page)
    }

    pub fn cache_stats(&self) -> CacheStats {
        CacheStats {
            first_page_hits: self.first_page_hits.load(Ordering::Relaxed),
            cached_first_pages: self
                .first_page_cache
                .lock()
                .map(|cache| cache.pages.len())
                .unwrap_or(0),
        }
    }

    /// Prepares a viewport while reusing this reader's first-page cache.
    pub fn open_viewport_cached(
        &self,
        path: impl AsRef<Path>,
    ) -> Result<DesktopViewport, Box<dyn std::error::Error>> {
        let path = path.as_ref();
        let title = path
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_else(|| "Untitled PDF".to_owned());
        Ok(DesktopViewport {
            title,
            page: self.first_page_cached(path)?,
        })
    }

    /// Returns cached classification and signature metadata for an unchanged
    /// file during this reader session.
    pub fn inspect_cached(
        &self,
        path: impl AsRef<Path>,
    ) -> Result<DocumentInspection, Box<dyn std::error::Error>> {
        let path = path.as_ref();
        let metadata = std::fs::metadata(path)?;
        let file_size = metadata.len();
        let modified = metadata.modified().ok();
        let key = path.to_path_buf();
        let cache = self
            .inspection_cache
            .lock()
            .map_err(|_| std::io::Error::other("inspection cache lock poisoned"))?;
        if let Some(cached) = cache.get(&key) {
            if cached.file_size == file_size && cached.modified == modified {
                return Ok(cached.value.clone());
            }
        }
        drop(cache);

        let bytes = self.read_bytes_cached(path)?;
        let value = Self::inspect_bytes(&bytes)?;
        let mut cache = self
            .inspection_cache
            .lock()
            .map_err(|_| std::io::Error::other("inspection cache lock poisoned"))?;
        if self.first_page_cache_capacity > 0 && cache.len() >= self.first_page_cache_capacity {
            if let Some(oldest) = cache.keys().next().cloned() {
                cache.remove(&oldest);
            }
        }
        cache.insert(
            key,
            CachedInspection {
                file_size,
                modified,
                value: value.clone(),
            },
        );
        Ok(value)
    }

    /// Opens a document while reusing this reader's bounded byte cache.
    pub fn open_cached(
        &self,
        path: impl AsRef<Path>,
    ) -> Result<Document, Box<dyn std::error::Error>> {
        let path = path.as_ref();
        let metadata = std::fs::metadata(path)?;
        let file_size = metadata.len();
        let modified = metadata.modified().ok();
        let key = path.to_path_buf();
        {
            let cache = self
                .document_cache
                .lock()
                .map_err(|_| std::io::Error::other("document cache lock poisoned"))?;
            if let Some(cached) = cache.get(&key) {
                if cached.file_size == file_size && cached.modified == modified {
                    return Ok(cached.value.clone());
                }
            }
        }
        let bytes = self.read_bytes_cached(path)?;
        let value = Self::open_bytes(&bytes)?;
        let mut cache = self
            .document_cache
            .lock()
            .map_err(|_| std::io::Error::other("document cache lock poisoned"))?;
        if self.first_page_cache_capacity > 0 && cache.len() >= self.first_page_cache_capacity {
            if let Some(oldest) = cache.keys().next().cloned() {
                cache.remove(&oldest);
            }
        }
        cache.insert(
            key,
            CachedDocument {
                file_size,
                modified,
                value: value.clone(),
            },
        );
        Ok(value)
    }

    /// Renders a first page while reusing this reader's bounded byte cache.
    pub fn render_first_page_cached(
        &self,
        path: impl AsRef<Path>,
    ) -> Result<RenderedPage, Box<dyn std::error::Error>> {
        let bytes = self.read_bytes_cached(path.as_ref())?;
        Self::render_first_page_bytes(&bytes)
    }

    fn read_bytes_cached(
        &self,
        path: &Path,
    ) -> Result<std::sync::Arc<[u8]>, Box<dyn std::error::Error>> {
        let metadata = std::fs::metadata(path)?;
        let file_size = metadata.len();
        let modified = metadata.modified().ok();
        let key = path.to_path_buf();
        let mut cache = self
            .bytes_cache
            .lock()
            .map_err(|_| std::io::Error::other("byte cache lock poisoned"))?;
        if let Some(cached) = cache.get(&key) {
            if cached.file_size == file_size && cached.modified == modified {
                return Ok(std::sync::Arc::clone(&cached.bytes));
            }
        }
        let bytes: std::sync::Arc<[u8]> = std::fs::read(path)?.into();
        if self.first_page_cache_capacity > 0 {
            if cache.len() >= self.first_page_cache_capacity {
                if let Some(oldest) = cache.keys().next().cloned() {
                    cache.remove(&oldest);
                }
            }
            cache.insert(
                key,
                CachedBytes {
                    file_size,
                    modified,
                    bytes: std::sync::Arc::clone(&bytes),
                },
            );
        }
        Ok(bytes)
    }

    /// Prepares the first viewport without constructing document Markdown.
    /// The window adapter owns platform-specific rendering; this portable seam
    /// gives it a title and text/raster routing result.
    pub fn open_viewport(
        path: impl AsRef<Path>,
    ) -> Result<DesktopViewport, Box<dyn std::error::Error>> {
        let path = path.as_ref();
        let title = path
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_else(|| "Untitled PDF".to_owned());
        Ok(DesktopViewport {
            title,
            page: Self::first_page(path)?,
        })
    }

    /// Opens just enough of a document to route it to the correct reader path.
    /// It never extracts text or constructs Markdown.
    pub fn inspect(
        path: impl AsRef<Path>,
    ) -> Result<DocumentInspection, Box<dyn std::error::Error>> {
        // One read serves both answers. Classification parses these bytes and
        // the signature marker is a substring of them, so reading the file a
        // second time only re-paid the I/O — ~14 ms on a 2.7 MB document.
        let path = path.as_ref();
        let bytes = std::fs::read(path).map_err(|error| format!("{}: {error}", path.display()))?;
        Self::inspect_bytes(&bytes)
    }

    pub fn inspect_bytes(bytes: &[u8]) -> Result<DocumentInspection, Box<dyn std::error::Error>> {
        let result = detect_pdf_mem_scoped(bytes)?;
        Ok(DocumentInspection {
            page_count: result.page_count,
            kind: document_kind(result.pdf_type),
            has_signature: has_signature_marker(bytes),
            processing_time_ms: result.processing_time_ms,
        })
    }

    /// Decodes only the first page into a text layer for the initial viewport.
    pub fn first_page(path: impl AsRef<Path>) -> Result<PageTextLayer, Box<dyn std::error::Error>> {
        let bytes = std::fs::read(path)?;
        Self::first_page_bytes(&bytes)
    }

    pub fn first_page_bytes(bytes: &[u8]) -> Result<PageTextLayer, Box<dyn std::error::Error>> {
        let result = process_first_page_mem(bytes)?;
        if first_page_requires_raster(
            document_kind(result.pdf_type),
            result.pages_needing_ocr.contains(&1),
        ) {
            return Ok(PageTextLayer {
                page_number: 1,
                text: String::new(),
                has_rotation: false,
                requires_raster: true,
            });
        }

        let has_rotation = result
            .items
            .iter()
            .any(|item| item.rotation.rem_euclid(180.0) > 1.0);
        let text = if result.items.len() == 1 {
            result.items.into_iter().next().unwrap().text
        } else {
            let mut text = String::with_capacity(
                result
                    .items
                    .iter()
                    .map(|item| item.text.len())
                    .sum::<usize>(),
            );
            for item in result.items {
                text.push_str(&item.text);
            }
            text
        };
        Ok(PageTextLayer {
            page_number: 1,
            text,
            has_rotation,
            requires_raster: false,
        })
    }

    /// Renders the first page through the native PDFium path at 150 DPI.
    /// The returned bitmap is owned and ready for a desktop viewport or an
    /// encoder; no text extraction or Markdown construction is performed.
    pub fn render_first_page(
        path: impl AsRef<Path>,
    ) -> Result<RenderedPage, Box<dyn std::error::Error>> {
        let bytes = std::fs::read(path)?;
        Self::render_first_page_bytes(&bytes)
    }

    pub fn render_first_page_bytes(
        bytes: &[u8],
    ) -> Result<RenderedPage, Box<dyn std::error::Error>> {
        static RENDERER: OnceLock<Result<PdfiumRenderer, String>> = OnceLock::new();
        let renderer = match RENDERER
            .get_or_init(|| PdfiumRenderer::load().map_err(|error| error.to_string()))
        {
            Ok(renderer) => *renderer,
            Err(error) => return Err(std::io::Error::other(error.clone()).into()),
        };
        let mut pages = renderer.render_pages(bytes, &[1], None, &RenderOptions::new())?;
        pages
            .pop()
            .ok_or_else(|| std::io::Error::other("PDFium returned no first page").into())
    }

    pub fn open(path: impl AsRef<Path>) -> Result<Document, Box<dyn std::error::Error>> {
        let bytes = std::fs::read(path)?;
        Self::open_bytes(&bytes)
    }

    pub fn open_bytes(bytes: &[u8]) -> Result<Document, Box<dyn std::error::Error>> {
        // The markdown cleanup regexes cost ~10.7 ms to build on first use,
        // and that use is at the very end of the pipeline. Build them
        // alongside the parse so a document that needs them has them ready.
        //
        // Deliberately not joined. The cleanup passes now skip the build
        // entirely for a document that cannot need it (no line-break hyphen,
        // no URL, no dot leader), and waiting here would hand that document
        // back the very cost those guards remove — measured as a 23%
        // regression on the image-based fixture, which emits no markdown at
        // all. Detached, the work is free to the documents that skip it and
        // already under way for the ones that do not: the pipeline's own
        // first use blocks on the same `once_cell` static either way.
        if MARKDOWN_WARMUP_STARTED.set(()).is_ok() {
            std::thread::spawn(pdf_inspector::markdown::warm_markdown_pipeline);
        }
        let result = process_pdf_mem(bytes)?;
        let markdown = result.markdown.unwrap_or_default();
        let first_page_text = markdown
            .split("<!-- Page ")
            .next()
            .unwrap_or_default()
            .trim()
            .to_owned();
        Ok(Document {
            page_count: result.page_count,
            kind: document_kind(result.pdf_type),
            first_page_text,
            markdown,
            processing_time_ms: result.processing_time_ms,
        })
    }
}

fn document_kind(pdf_type: PdfType) -> DocumentKind {
    match pdf_type {
        PdfType::TextBased => DocumentKind::Text,
        PdfType::ImageBased | PdfType::Scanned => DocumentKind::Image,
        PdfType::Mixed => DocumentKind::Mixed,
    }
}

/// Decides whether the first viewport should bypass text-layer extraction.
/// OCR work is scheduled separately from the latency-critical first paint.
pub fn first_page_requires_raster(kind: DocumentKind, page_needs_ocr: bool) -> bool {
    matches!(kind, DocumentKind::Image) || page_needs_ocr
}

/// Classification over bytes already read, with the page-scoped strategy the
/// routing tiers want: `inspect` answers "which reader path does this take",
/// and that question is settled by the pages a viewer opens first, not by a
/// sample spread across a long document.
struct InspectionDetection {
    pdf_type: PdfType,
    page_count: u32,
    processing_time_ms: u64,
}

fn detect_pdf_mem_scoped(bytes: &[u8]) -> Result<InspectionDetection, pdf_inspector::PdfError> {
    let detection = DetectionConfig {
        // A one- or two-page PDF cannot hide a later page from a sample, so
        // keep the launch-critical classifier to one page for that common
        // small-file case. Longer documents retain the three-page
        // cover/middle/last sample. The detector chooses after parsing, using
        // the authoritative page count instead of rescanning all raw bytes.
        strategy: ScanStrategy::AdaptiveSample {
            short_document_max_pages: 2,
            short_document_sample_size: 1,
            long_document_sample_size: INSPECT_SAMPLE_PAGES,
        },
        ..DetectionConfig::default()
    };
    let started = std::time::Instant::now();
    let result = detect_pdf_routing_mem_with_config(bytes, detection)?;
    Ok(InspectionDetection {
        pdf_type: result.pdf_type,
        page_count: result.page_count,
        processing_time_ms: started.elapsed().as_millis() as u64,
    })
}

/// Pages sampled by [`Reader::inspect`]. The library default is 8, chosen so
/// an annual report with an image-only cover is not called scanned; 3 keeps
/// that protection (cover, middle, last are what `distribute_pages` picks
/// first) while cutting the content scans a long document pays for a routing
/// decision.
const INSPECT_SAMPLE_PAGES: u32 = 3;

/// Whether a PDF signature field or signature dictionary marker appears in
/// the file's bytes, so the lightweight open path can select the
/// signed-document UI without constructing a full object graph.
///
/// Every marker ends in `/Sig`, so the SIMD scan skips directly between that
/// rare four-byte suffix before confirming the full marker. Searching only
/// for `S` leaves thousands of false candidates in compressed image streams.
fn has_signature_marker(bytes: &[u8]) -> bool {
    const MARKERS: [&[u8]; 4] = [b"/FT/Sig", b"/FT /Sig", b"/Type/Sig", b"/Type /Sig"];
    const NEEDLE: &[u8] = b"/Sig";

    memchr::memmem::find_iter(bytes, NEEDLE).any(|start| {
        MARKERS.iter().any(|marker| {
            let prefix = marker.len() - NEEDLE.len();
            start >= prefix && &bytes[start - prefix..start + NEEDLE.len()] == *marker
        })
    })
}
