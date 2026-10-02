use blazepdf::{DocumentInspection, Reader};
use std::{
    fs::File,
    io::{BufWriter, Write},
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let mode = args.next();
    let inspect_only = mode.as_deref() == Some("--inspect");
    let first_page_only = mode.as_deref() == Some("--first-page");
    let render_only = mode.as_deref() == Some("--render");
    let path = if inspect_only || first_page_only || render_only {
        args.next()
    } else {
        mode
    }
    .ok_or("usage: blazepdf [--inspect|--first-page] <document.pdf>")?;

    if inspect_only {
        let document = Reader::inspect(path)?;
        write_inspection(std::io::stdout().lock(), &document)?;
        return Ok(());
    }
    if first_page_only {
        let page = Reader::first_page(path)?;
        println!(
            "page: {}\nrotated: {}\n\n{}",
            page.page_number, page.has_rotation, page.text
        );
        return Ok(());
    }
    if render_only {
        let output = args
            .next()
            .ok_or("usage: blazepdf --render <document.pdf> [output.ppm]")?;
        let page = Reader::render_first_page(path)?;
        if page.format() != pdf_inspector::vision::RenderPixelFormat::Rgb8 {
            return Err("native renderer returned a non-RGB bitmap".into());
        }
        let mut file = BufWriter::with_capacity(1024 * 1024, File::create(output)?);
        write_ppm(
            &mut file,
            page.width(),
            page.height(),
            page.stride(),
            page.pixels(),
        )?;
        file.flush()?;
        return Ok(());
    }
    let document = Reader::open(path)?;
    println!(
        "pages: {}\nkind: {:?}\nprocessed: {} ms\n\n{}",
        document.page_count, document.kind, document.processing_time_ms, document.markdown
    );
    Ok(())
}

fn write_inspection(mut output: impl Write, document: &DocumentInspection) -> std::io::Result<()> {
    let metadata = format!(
        "pages: {}\nkind: {:?}\nsigned: {}\nprocessed: {} ms\n",
        document.page_count, document.kind, document.has_signature, document.processing_time_ms
    );
    output.write_all(metadata.as_bytes())
}

fn write_ppm(
    mut output: impl Write,
    width: u32,
    height: u32,
    stride: usize,
    pixels: &[u8],
) -> std::io::Result<()> {
    write!(output, "P6\n{width} {height}\n255\n")?;
    let row_bytes = width as usize * 3;
    if stride == row_bytes {
        return output.write_all(pixels);
    }
    for row in pixels.chunks(stride) {
        output.write_all(&row[..row_bytes])?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{write_inspection, write_ppm};
    use blazepdf::{DocumentInspection, DocumentKind};
    use std::io::{self, Write};

    #[test]
    fn inspection_metadata_is_complete_in_one_sink_write() {
        #[derive(Default)]
        struct Sink {
            bytes: Vec<u8>,
            writes: usize,
        }
        impl Write for Sink {
            fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
                self.writes += 1;
                self.bytes.extend_from_slice(bytes);
                Ok(bytes.len())
            }
            fn flush(&mut self) -> io::Result<()> {
                Ok(())
            }
        }
        let mut output = Sink::default();
        let document = DocumentInspection {
            page_count: 12,
            kind: DocumentKind::Text,
            has_signature: true,
            processing_time_ms: 37,
        };
        write_inspection(&mut output, &document).unwrap();
        assert_eq!(
            output.bytes,
            b"pages: 12\nkind: Text\nsigned: true\nprocessed: 37 ms\n"
        );
        assert_eq!(
            output.writes, 1,
            "avoid fragmented writes to the output sink"
        );
    }

    #[test]
    fn writes_tight_rgb_rows_in_one_payload() {
        let mut output = Vec::new();
        write_ppm(&mut output, 2, 1, 6, &[1, 2, 3, 4, 5, 6]).unwrap();
        assert_eq!(output, b"P6\n2 1\n255\n\x01\x02\x03\x04\x05\x06");
    }

    #[test]
    fn omits_padding_from_strided_rgb_rows() {
        let mut output = Vec::new();
        write_ppm(&mut output, 1, 2, 4, &[1, 2, 3, 99, 4, 5, 6, 99]).unwrap();
        assert_eq!(output, b"P6\n1 2\n255\n\x01\x02\x03\x04\x05\x06");
    }
}
