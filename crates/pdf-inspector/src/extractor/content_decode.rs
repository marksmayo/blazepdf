//! Bounded content-stream decoding.
//!
//! `lopdf::content::Content::decode` materializes every operator before any
//! caller can apply a limit. A compact page of `q Q` pairs can therefore
//! allocate hundreds of megabytes and abort. Count operators first (without
//! allocating `Operation` objects) and skip decode when the cap is exceeded.

use crate::PdfError;
use lopdf::content::Content;
use std::borrow::Cow;

/// Maximum content-stream operators decoded for a page or a single Form
/// XObject. Matches the previous post-decode skip threshold.
pub(crate) const MAX_PAGE_OPERATIONS: usize = 1_000_000;

/// Maximum decompressed bytes read for a page's content, and for each Form
/// XObject read on its own, so a content bomb (a tiny Flate stream
/// inflating to gigabytes) skips the page or the form instead of exhausting
/// memory — the same degradation as the operator cap. Real page content
/// runs a few MB at most; the bound is deliberately far above that.
pub(crate) const MAX_PAGE_CONTENT_BYTES: usize = 64 * 1024 * 1024;

/// Scheduling only: byte/operator safety limits are enforced independently.
pub(crate) fn parallel_stream_work(stream_count: usize, bytes: usize) -> bool {
    stream_count > 1 && bytes >= 256 * 1024
}

/// Decode `data` unless it contains more than `max_operations` operators.
///
/// Returns `Ok(None)` when the stream exceeds the cap, so callers can skip
/// extraction without first allocating the operation vector.
pub(crate) fn decode_content_bounded(
    data: &[u8],
    max_operations: usize,
) -> Result<Option<Content>, PdfError> {
    if content_exceeds_operation_limit(data, max_operations) {
        return Ok(None);
    }
    Content::decode(data)
        .map(Some)
        .map_err(|e| PdfError::Parse(e.to_string()))
}

/// Decode content after discarding non-clipping vector paths beyond the
/// caller's useful geometry limit. Text, graphics state, images, and every
/// clipping path remain byte-for-byte present in the compacted stream.
pub(crate) fn decode_content_bounded_with_path_limit(
    data: &[u8],
    max_operations: usize,
    path_limit: usize,
) -> Result<Option<Content>, PdfError> {
    let (compacted, operator_count, _) =
        compact_excessive_non_clipping_paths_counted(data, path_limit);
    if operator_count > max_operations {
        return Ok(None);
    }
    Content::decode(compacted.as_ref())
        .map(Some)
        .map_err(|error| PdfError::Parse(error.to_string()))
}

/// Decode independently inflated page-content streams concurrently while
/// preserving their array order and the page-wide safety/geometry limits.
///
/// PDF content arrays are logically concatenated, so a producer may split an
/// operand list or an open path across streams.  Strict per-part parsing and
/// the boundary-complete scan keep that unusual case on the exact joined
/// fallback; ordinary self-contained streams avoid the large joined buffer
/// and parallelise lopdf's operation materialisation.
pub(crate) fn decode_content_parts_bounded_with_path_limit(
    parts: &[&[u8]],
    max_operations: usize,
    path_limit: usize,
) -> Result<Option<Content>, PdfError> {
    use rayon::prelude::*;

    if parts.len() <= 1 {
        return decode_content_bounded_with_path_limit(
            parts.first().copied().unwrap_or_default(),
            max_operations,
            path_limit,
        );
    }

    let total_bytes = parts
        .iter()
        .fold(0usize, |total, part| total.saturating_add(part.len()));
    let parallel = parallel_stream_work(parts.len(), total_bytes);
    let scan_part = |part: &&[u8]| scan_non_clipping_paths(part, true);
    let scans: Vec<_> = if parallel {
        parts.par_iter().map(scan_part).collect()
    } else {
        parts.iter().map(scan_part).collect()
    };
    let operator_count = scans
        .iter()
        .try_fold(0usize, |total, scan| total.checked_add(scan.operator_count));
    let candidate_line_segments = scans.iter().try_fold(0usize, |total, scan| {
        total.checked_add(scan.candidate_line_segments)
    });
    let can_decode_independently = scans.iter().all(|scan| scan.boundary_complete)
        && operator_count.is_some()
        && candidate_line_segments.is_some();

    if can_decode_independently {
        let operator_count = operator_count.unwrap_or(usize::MAX);
        if operator_count > max_operations {
            return Ok(None);
        }
        let drop_paths = candidate_line_segments.unwrap_or(usize::MAX) > path_limit;
        let decode_part = |(part, scan): (&&[u8], NonClippingPathScan)| {
            let compacted =
                compact_paths_from_scan(part, scan, if drop_paths { 0 } else { usize::MAX });
            Content::decode_strict(compacted.as_ref())
        };
        let decoded: Result<Vec<Content>, lopdf::Error> = if parallel {
            parts
                .par_iter()
                .zip(scans.into_par_iter())
                .map(decode_part)
                .collect()
        } else {
            parts.iter().zip(scans).map(decode_part).collect()
        };
        if let Ok(decoded) = decoded {
            let operation_count = decoded.iter().map(|content| content.operations.len()).sum();
            let mut operations = Vec::with_capacity(operation_count);
            for mut content in decoded {
                operations.append(&mut content.operations);
            }
            return Ok(Some(Content { operations }));
        }
    }

    let joined_len = parts
        .iter()
        .fold(0usize, |total, part| total.saturating_add(part.len() + 1));
    let mut joined = Vec::with_capacity(joined_len);
    for part in parts {
        joined.extend_from_slice(part);
        joined.push(b'\n');
    }
    decode_content_bounded_with_path_limit(&joined, max_operations, path_limit)
}

#[cfg(test)]
fn compact_excessive_non_clipping_paths(data: &[u8], path_limit: usize) -> Cow<'_, [u8]> {
    compact_excessive_non_clipping_paths_counted(data, path_limit).0
}

fn compact_excessive_non_clipping_paths_counted(
    data: &[u8],
    path_limit: usize,
) -> (Cow<'_, [u8]>, usize, usize) {
    let scan = scan_non_clipping_paths(data, true);
    let operator_count = scan.operator_count;
    let candidate_line_segments = scan.candidate_line_segments;
    (
        compact_paths_from_scan(data, scan, path_limit),
        operator_count,
        candidate_line_segments,
    )
}

fn compact_paths_from_scan(
    data: &[u8],
    mut scan: NonClippingPathScan,
    path_limit: usize,
) -> Cow<'_, [u8]> {
    // Unpainted, non-clipping paths cannot contribute extraction geometry.
    // Reuse the initial scan rather than tokenizing large parts a second time.
    if scan.candidate_line_segments <= path_limit {
        scan.stroke_candidates.clear();
    }
    scan.stroke_candidates
        .append(&mut scan.unpainted_candidates);
    if scan.stroke_candidates.is_empty() {
        return Cow::Borrowed(data);
    }
    scan.stroke_candidates
        .sort_unstable_by_key(|&(start, _)| start);
    let dropped_bytes = scan
        .stroke_candidates
        .iter()
        .map(|(start, end)| end - start)
        .sum::<usize>();
    let mut compacted = Vec::with_capacity(data.len().saturating_sub(dropped_bytes));
    let mut cursor = 0usize;
    for (start, end) in scan.stroke_candidates {
        compacted.extend_from_slice(&data[cursor..start]);
        cursor = end;
    }
    compacted.extend_from_slice(&data[cursor..]);
    Cow::Owned(compacted)
}

struct NonClippingPathScan {
    operator_count: usize,
    candidate_line_segments: usize,
    stroke_candidates: Vec<(usize, usize)>,
    unpainted_candidates: Vec<(usize, usize)>,
    boundary_complete: bool,
}

fn scan_non_clipping_paths(data: &[u8], collect_candidates: bool) -> NonClippingPathScan {
    let mut index = 0usize;
    let mut instruction_start = 0usize;
    let mut path_start = None;
    let mut path_clips = false;
    let mut path_has_rectangle = false;
    let mut path_interleaved = false;
    let mut path_line_segments = 0usize;
    let mut candidate_line_segments = 0usize;
    let mut stroke_candidates = Vec::new();
    let mut unpainted_candidates = Vec::new();
    let mut operator_count = 0usize;

    while index < data.len() {
        skip_content_space(data, &mut index);
        if index >= data.len() {
            break;
        }
        if data[index] == b'%' {
            skip_comment(data, &mut index);
            continue;
        }
        match data[index] {
            b'(' => index = skip_literal_string(data, index),
            b'<' => {
                if data.get(index + 1) == Some(&b'<') {
                    index += 2;
                } else {
                    index = skip_hex_string(data, index);
                }
            }
            b'>' => {
                index += 1;
                if data.get(index) == Some(&b'>') {
                    index += 1;
                }
            }
            b'[' | b']' => index += 1,
            b'/' => skip_name(data, &mut index),
            b'+' | b'-' | b'.' => skip_number(data, &mut index),
            byte if byte.is_ascii_digit() => skip_number(data, &mut index),
            byte if is_operator_byte(byte) => {
                let operator_start = index;
                index += 1;
                while index < data.len() && is_operator_byte(data[index]) {
                    index += 1;
                }
                let operator = &data[operator_start..index];
                if matches!(operator, b"true" | b"false" | b"null") {
                    continue;
                }
                operator_count += 1;

                let constructs_path =
                    matches!(operator, b"m" | b"l" | b"c" | b"v" | b"y" | b"h" | b"re");
                let clips_path = matches!(operator, b"W" | b"W*");
                let ends_path = matches!(
                    operator,
                    b"S" | b"s" | b"f" | b"F" | b"f*" | b"B" | b"B*" | b"b" | b"b*" | b"n"
                );

                if constructs_path {
                    path_start.get_or_insert(instruction_start);
                    path_has_rectangle |= operator == b"re";
                    path_line_segments += usize::from(matches!(operator, b"l" | b"h"));
                } else if clips_path && path_start.is_some() {
                    path_clips = true;
                } else if ends_path {
                    if let Some(start) = path_start.take() {
                        if matches!(operator, b"S" | b"s")
                            && !path_clips
                            && !path_has_rectangle
                            && !path_interleaved
                        {
                            candidate_line_segments += path_line_segments;
                            if collect_candidates {
                                stroke_candidates.push((start, index));
                            }
                        }
                        if operator == b"n"
                            && !path_clips
                            && !path_interleaved
                            && collect_candidates
                        {
                            unpainted_candidates.push((start, index));
                        }
                    }
                    path_clips = false;
                    path_has_rectangle = false;
                    path_line_segments = 0;
                    path_interleaved = false;
                } else if path_start.is_some() {
                    // Never swallow text, transforms or graphics state nested
                    // between construction and painting of a path.
                    path_interleaved = true;
                }
                instruction_start = index;

                if operator == b"BI" && (index >= data.len() || is_content_space(data[index])) {
                    index = skip_inline_image_after_bi(data, index);
                    instruction_start = index;
                }
            }
            _ => index += 1,
        }
    }

    NonClippingPathScan {
        operator_count,
        candidate_line_segments,
        stroke_candidates,
        unpainted_candidates,
        boundary_complete: path_start.is_none(),
    }
}

fn content_exceeds_operation_limit(data: &[u8], max_operations: usize) -> bool {
    count_content_operators(data, max_operations.saturating_add(1)) > max_operations
}

/// Count operators using the same token rules as lopdf's content parser,
/// stopping at `limit`. Does not allocate `Operation` / `Object` values.
fn count_content_operators(data: &[u8], limit: usize) -> usize {
    let mut i = 0;
    let mut count = 0;
    while i < data.len() && count < limit {
        skip_content_space(data, &mut i);
        if i >= data.len() {
            break;
        }
        if data[i] == b'%' {
            skip_comment(data, &mut i);
            continue;
        }
        match data[i] {
            b'(' => i = skip_literal_string(data, i),
            b'<' => {
                if data.get(i + 1) == Some(&b'<') {
                    i += 2;
                } else {
                    i = skip_hex_string(data, i);
                }
            }
            b'>' => {
                i += 1;
                if data.get(i) == Some(&b'>') {
                    i += 1;
                }
            }
            b'[' | b']' => i += 1,
            b'/' => skip_name(data, &mut i),
            b'+' | b'-' | b'.' => skip_number(data, &mut i),
            b if b.is_ascii_digit() => skip_number(data, &mut i),
            b if is_operator_byte(b) => {
                let start = i;
                i += 1;
                while i < data.len() && is_operator_byte(data[i]) {
                    i += 1;
                }
                let token = &data[start..i];
                if token == b"true" || token == b"false" || token == b"null" {
                    continue;
                }
                count += 1;
                if token == b"BI" && (i >= data.len() || is_content_space(data[i])) {
                    i = skip_inline_image_after_bi(data, i);
                }
            }
            _ => i += 1,
        }
    }
    count
}

fn is_content_space(b: u8) -> bool {
    // PDF whitespace (ISO 32000): NUL, tab, LF, FF, CR, space. Names must
    // stop on these so a following operator is not absorbed into `/Name`.
    matches!(b, b'\0' | b'\t' | b'\n' | b'\x0c' | b'\r' | b' ')
}

fn is_operator_byte(b: u8) -> bool {
    b.is_ascii_alphabetic() || matches!(b, b'*' | b'\'' | b'"')
}

fn is_delimiter(b: u8) -> bool {
    matches!(
        b,
        b'(' | b')' | b'<' | b'>' | b'[' | b']' | b'{' | b'}' | b'/' | b'%'
    )
}

fn skip_content_space(data: &[u8], i: &mut usize) {
    while *i < data.len() && is_content_space(data[*i]) {
        *i += 1;
    }
}

fn skip_comment(data: &[u8], i: &mut usize) {
    while *i < data.len() && data[*i] != b'\n' && data[*i] != b'\r' {
        *i += 1;
    }
}

fn skip_literal_string(data: &[u8], mut i: usize) -> usize {
    let mut depth = 1i32;
    i += 1;
    while i < data.len() && depth > 0 {
        match data[i] {
            b'\\' => {
                i += 1;
                if i < data.len() {
                    i += 1;
                }
            }
            b'(' => {
                depth += 1;
                i += 1;
            }
            b')' => {
                depth -= 1;
                i += 1;
            }
            _ => i += 1,
        }
    }
    i
}

fn skip_hex_string(data: &[u8], mut i: usize) -> usize {
    i += 1;
    while i < data.len() && data[i] != b'>' {
        i += 1;
    }
    if i < data.len() {
        i += 1;
    }
    i
}

fn skip_name(data: &[u8], i: &mut usize) {
    *i += 1;
    while *i < data.len() && !is_content_space(data[*i]) && !is_delimiter(data[*i]) {
        *i += 1;
    }
}

fn skip_number(data: &[u8], i: &mut usize) {
    if *i < data.len() && matches!(data[*i], b'+' | b'-') {
        *i += 1;
    }
    while *i < data.len() && data[*i].is_ascii_digit() {
        *i += 1;
    }
    if *i < data.len() && data[*i] == b'.' {
        *i += 1;
        while *i < data.len() && data[*i].is_ascii_digit() {
            *i += 1;
        }
    }
}

/// After a `BI` operator, skip inline-image data through `EI`.
/// Uses the same PDF whitespace set as `is_content_space`. If `EI` is not
/// found, leave the cursor in place so later operators are still counted
/// (undercounting would let decode allocate the full vector).
fn skip_inline_image_after_bi(data: &[u8], mut i: usize) -> usize {
    skip_content_space(data, &mut i);
    let rest = &data[i..];
    if let Some(pos) = rest.windows(4).position(|w| {
        is_content_space(w[0]) && w[1] == b'E' && w[2] == b'I' && is_content_space(w[3])
    }) {
        return i + pos + 3;
    }
    i
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn small_stream_arrays_do_not_pay_parallel_scheduling_costs() {
        assert!(!parallel_stream_work(8, 8 * 1024));
        assert!(!parallel_stream_work(1, 8 * 1024 * 1024));
        assert!(parallel_stream_work(8, 8 * 1024 * 1024));
    }

    #[test]
    fn compaction_preserves_text_interleaved_inside_a_stroked_path() {
        let decoded = decode_content_bounded_with_path_limit(
            b"0 0 m 1 1 l BT (kept) Tj ET S 2 2 m 3 3 l S",
            100,
            0,
        )
        .unwrap()
        .unwrap();
        let operators: Vec<_> = decoded
            .operations
            .iter()
            .map(|op| op.operator.as_str())
            .collect();
        assert_eq!(operators, ["m", "l", "BT", "Tj", "ET", "S"]);
        assert_eq!(decoded.operations[3].operands[0].as_str().unwrap(), b"kept");
    }

    #[test]
    fn unpainted_paths_are_not_materialized_but_clipping_paths_survive() {
        let decoded = decode_content_bounded_with_path_limit(
            b"0 0 m 1 1 l n BT (kept) Tj ET 2 2 m 3 3 l W n",
            100,
            100,
        )
        .unwrap()
        .unwrap();
        let operators: Vec<_> = decoded
            .operations
            .iter()
            .map(|op| op.operator.as_str())
            .collect();
        assert_eq!(operators, ["BT", "Tj", "ET", "m", "l", "W", "n"]);
    }

    #[test]
    fn excessive_non_clipping_paths_are_compacted_but_text_and_clips_survive() {
        let content = b"0 0 m 1 1 l S 2 2 m 3 3 l 4 4 l S BT (hello) Tj ET \
            5 5 m 6 6 l W n";

        let compacted = compact_excessive_non_clipping_paths(content, 2);
        let decoded = Content::decode(compacted.as_ref()).unwrap();
        let operators: Vec<&str> = decoded
            .operations
            .iter()
            .map(|operation| operation.operator.as_str())
            .collect();

        assert_eq!(operators, ["BT", "Tj", "ET", "m", "l", "W", "n"]);
    }

    #[test]
    fn independent_content_parts_keep_order_and_share_the_page_path_limit() {
        let parts: &[&[u8]] = &[
            b"0 0 m 1 1 l 2 2 l S BT (first) Tj ET",
            b"3 3 m 4 4 l 5 5 l S BT (second) Tj ET",
        ];

        let decoded = decode_content_parts_bounded_with_path_limit(parts, 100, 3)
            .unwrap()
            .unwrap();
        let operators: Vec<&str> = decoded
            .operations
            .iter()
            .map(|operation| operation.operator.as_str())
            .collect();
        let text: Vec<&[u8]> = decoded
            .operations
            .iter()
            .filter(|operation| operation.operator == "Tj")
            .map(|operation| operation.operands[0].as_str().unwrap())
            .collect();

        assert_eq!(operators, ["BT", "Tj", "ET", "BT", "Tj", "ET"]);
        assert_eq!(text, [b"first".as_slice(), b"second".as_slice()]);
    }

    #[test]
    fn split_operands_fall_back_to_joined_content_semantics() {
        let parts: &[&[u8]] = &[b"10 20", b"m 30 40 l S"];

        let decoded = decode_content_parts_bounded_with_path_limit(parts, 10, 10)
            .unwrap()
            .unwrap();

        assert_eq!(decoded.operations[0].operator, "m");
        assert_eq!(decoded.operations[0].operands.len(), 2);
        assert_eq!(decoded.operations[0].operands[0].as_i64().unwrap(), 10);
        assert_eq!(decoded.operations[0].operands[1].as_i64().unwrap(), 20);
        assert_eq!(decoded.operations[1].operator, "l");
        assert_eq!(decoded.operations[2].operator, "S");
    }

    fn lopdf_op_count(data: &[u8]) -> usize {
        Content::decode(data)
            .map(|c| c.operations.len())
            .unwrap_or(0)
    }

    /// DoS safety: never report fewer operators than lopdf would allocate.
    /// Overcount is acceptable (skip a page); undercount would re-open decode.
    fn assert_count_does_not_undercount(data: &[u8]) {
        let ours = count_content_operators(data, usize::MAX);
        match Content::decode(data) {
            Ok(content) => assert!(
                ours >= content.operations.len(),
                "undercount: ours={ours} lopdf={} for {:?}",
                content.operations.len(),
                String::from_utf8_lossy(data)
            ),
            Err(_) => {}
        }
    }

    #[test]
    fn operator_count_matches_lopdf_for_typical_streams() {
        let samples: &[&[u8]] = &[
            b"q 1 0 0 1 0 0 cm BT /F1 12 Tf 72 720 Td (Hello) Tj ET Q",
            b"q Q q Q",
            b"BT /F1 12 Tf 12 TL 1 0 0 1 100 512 Tm (first) Tj (struck) ' ET",
            b"1 0 0 rg 0 0 10 10 re f",
            b"true false null q",
            b"% comment\nq Q\n",
            b"[ (a) 1 (b) ] TJ",
            b"1 0 0 1 0 0 cm /Im0 Do",
        ];
        for data in samples {
            assert_eq!(
                count_content_operators(data, usize::MAX),
                lopdf_op_count(data),
                "count mismatch for {}",
                String::from_utf8_lossy(data)
            );
        }
    }

    #[test]
    fn strings_and_comments_are_not_operators() {
        let data = b"(q Q Tj) Tj % q Q\nET";
        assert_eq!(
            count_content_operators(data, usize::MAX),
            lopdf_op_count(data)
        );
        assert_eq!(count_content_operators(data, usize::MAX), 2); // Tj, ET
    }

    #[test]
    fn inline_image_counts_as_one_operator() {
        let data = b"BI /W 2 /H 2 /CS /RGB /BPC 8 ID \x00\x01\x02\x03 EI q";
        assert_eq!(
            count_content_operators(data, usize::MAX),
            lopdf_op_count(data)
        );
        assert_eq!(count_content_operators(data, usize::MAX), 2); // BI, q
    }

    #[test]
    fn inline_image_ei_accepts_pdf_whitespace() {
        let tab = b"BI /W 1 /H 1 ID \xff\tEI\t q Q";
        let nul = b"BI /W 1 /H 1 ID \xff\x00EI\x00 q Q";
        let ff = b"BI /W 1 /H 1 ID \xff\x0cEI\x0c q Q";
        for data in [tab.as_slice(), nul.as_slice(), ff.as_slice()] {
            assert_count_does_not_undercount(data);
            assert!(
                count_content_operators(data, usize::MAX) >= 3,
                "BI plus following q Q must remain visible after EI, got {} for {:?}",
                count_content_operators(data, usize::MAX),
                String::from_utf8_lossy(data)
            );
        }
    }

    #[test]
    fn decode_is_skipped_when_operator_cap_is_exceeded() {
        let mut data = Vec::new();
        for _ in 0..20 {
            data.extend_from_slice(b"q Q\n");
        }
        assert!(decode_content_bounded(&data, 10).unwrap().is_none());
        let decoded = decode_content_bounded(&data, 50).unwrap().unwrap();
        assert_eq!(decoded.operations.len(), 40);
    }

    #[test]
    fn name_whitespace_does_not_swallow_following_operator() {
        // NUL / form-feed end a name (PDF whitespace). Absorbing `q` into
        // `/x` would undercount and let decode allocate the operator vector.
        let mut nul_sep = Vec::new();
        let mut ff_sep = Vec::new();
        for _ in 0..8_000 {
            nul_sep.extend_from_slice(b"/x\x00q");
            ff_sep.extend_from_slice(b"/x\x0cq");
        }
        assert_count_does_not_undercount(&nul_sep);
        assert_count_does_not_undercount(&ff_sep);
        assert!(count_content_operators(&ff_sep, usize::MAX) >= 8_000);
    }

    #[test]
    fn edge_streams_do_not_undercount_vs_lopdf() {
        let samples: &[&[u8]] = &[
            b".5 0 0 .5 0 0 cm",
            b"+1 -2 3.0 rg",
            b"<0041> Tj",
            b"(unbalanced",
            b"BI /W 1 /H 1 ID \xff\xff no EI here q Q q Q",
            b"q\x00Q\x00q\x00Q",
            b"/F1\x0c12 Tf (Hi) Tj",
            b"{ 1 2 add } cvx",
        ];
        for data in samples {
            assert_count_does_not_undercount(data);
        }
    }

    #[test]
    fn million_q_pairs_are_rejected_without_decode() {
        let mut data = Vec::with_capacity((MAX_PAGE_OPERATIONS + 1) * 2);
        for _ in 0..=MAX_PAGE_OPERATIONS {
            data.extend_from_slice(b"q\n");
        }
        assert!(content_exceeds_operation_limit(&data, MAX_PAGE_OPERATIONS));
        assert!(decode_content_bounded(&data, MAX_PAGE_OPERATIONS)
            .unwrap()
            .is_none());
    }
}
