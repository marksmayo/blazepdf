//! Allocation traffic is a less load-sensitive signal than cold process timing.
use blazepdf::Reader;
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};

struct MeasuredAllocator;
static MEASURING: AtomicBool = AtomicBool::new(false);
static BYTES: AtomicU64 = AtomicU64::new(0);

unsafe impl GlobalAlloc for MeasuredAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if MEASURING.load(Ordering::Relaxed) {
            BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
        }
        unsafe { System.alloc(layout) }
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        unsafe { System.dealloc(pointer, layout) }
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        if MEASURING.load(Ordering::Relaxed) {
            BYTES.fetch_add(size as u64, Ordering::Relaxed);
        }
        unsafe { System.realloc(pointer, layout, size) }
    }
}

#[global_allocator]
static ALLOCATOR: MeasuredAllocator = MeasuredAllocator;

#[test]
fn vector_heavy_markdown_preserves_output_with_bounded_allocation_traffic() {
    let bytes = std::fs::read("vendors/CalyPdf/Caly.Benchmarks/fseprd1102849.pdf").unwrap();
    let expected = Reader::open_bytes(&bytes).unwrap();
    // A second warm call settles lazy caches and the background warmup.
    assert_eq!(
        Reader::open_bytes(&bytes).unwrap().markdown,
        expected.markdown
    );
    BYTES.store(0, Ordering::Relaxed);
    MEASURING.store(true, Ordering::SeqCst);
    let result = Reader::open_bytes(&bytes);
    MEASURING.store(false, Ordering::SeqCst);
    let allocated = BYTES.load(Ordering::Relaxed);
    let actual = result.unwrap();
    assert_eq!(actual.markdown, expected.markdown);
    assert_eq!(actual.kind, expected.kind);
    assert_eq!(actual.page_count, expected.page_count);
    eprintln!("vector-heavy allocation traffic: {allocated} bytes");
    // Page/column borrowing build: approximately 314.5 MB.
    assert!(
        allocated <= 314_440_000,
        "allocation traffic {allocated} exceeds budget"
    );
}
