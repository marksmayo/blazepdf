//! Resource regression gate on the public classification-only interface.
use blazepdf::{DocumentKind, Reader};
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};

struct MeasuredAllocator;
static MEASURING: AtomicBool = AtomicBool::new(false);
static BYTES: AtomicU64 = AtomicU64::new(0);
static CALLS: AtomicU64 = AtomicU64::new(0);

unsafe impl GlobalAlloc for MeasuredAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if MEASURING.load(Ordering::Relaxed) {
            BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
            CALLS.fetch_add(1, Ordering::Relaxed);
        }
        unsafe { System.alloc(layout) }
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        unsafe { System.dealloc(pointer, layout) }
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        if MEASURING.load(Ordering::Relaxed) {
            BYTES.fetch_add(size as u64, Ordering::Relaxed);
            CALLS.fetch_add(1, Ordering::Relaxed);
        }
        unsafe { System.realloc(pointer, layout, size) }
    }
}

#[global_allocator]
static ALLOCATOR: MeasuredAllocator = MeasuredAllocator;

#[test]
fn ordinary_text_inspection_keeps_metadata_with_bounded_allocations() {
    let bytes = std::fs::read("vendors/CalyPdf/Caly.Benchmarks/2559 words.pdf").unwrap();
    Reader::inspect_bytes(&bytes).unwrap();
    BYTES.store(0, Ordering::Relaxed);
    CALLS.store(0, Ordering::Relaxed);
    MEASURING.store(true, Ordering::SeqCst);
    let result = Reader::inspect_bytes(&bytes);
    MEASURING.store(false, Ordering::SeqCst);
    let actual = result.unwrap();
    assert_eq!(actual.page_count, 1);
    assert_eq!(actual.kind, DocumentKind::Text);
    assert!(!actual.has_signature);
    let allocated = BYTES.load(Ordering::Relaxed);
    let calls = CALLS.load(Ordering::Relaxed);
    eprintln!("text inspection: {allocated} bytes / {calls} allocation calls");
    // Repair indexing reduced 1,154 to 1,146; count pages without a temporary map.
    assert!(
        calls <= 1_145,
        "inspection allocation calls {calls} exceed budget"
    );
}
