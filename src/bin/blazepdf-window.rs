use blazepdf::{DesktopViewport, Reader};
use std::{
    io::Write,
    path::PathBuf,
    sync::{Arc, Mutex, OnceLock},
};

struct BlazeWindow {
    viewport: Option<DesktopViewport>,
    pending: Option<Arc<Mutex<Option<Result<DesktopViewport, String>>>>>,
    path: Option<PathBuf>,
    ready_reported: bool,
    first_frame_rendered: bool,
    load_started: bool,
    native_title_set: bool,
    benchmark_ready: bool,
    minimal_startup: bool,
    fonts_initialized: bool,
    error: Option<String>,
}

impl eframe::App for BlazeWindow {
    fn clear_color(&self, _visuals: &eframe::egui::Visuals) -> [f32; 4] {
        // eframe's default clear is translucent to support transparent
        // windows. This viewport is always opaque, so avoid the unnecessary
        // alpha composition on its first, intentionally blank frame.
        [12.0 / 255.0, 12.0 / 255.0, 12.0 / 255.0, 1.0]
    }

    fn update(&mut self, context: &eframe::egui::Context, _frame: &mut eframe::Frame) {
        if !self.first_frame_rendered {
            self.first_frame_rendered = true;
            if self.benchmark_ready && !self.ready_reported {
                println!("BLAZEPDF_FIRST_FRAME_READY");
                let _ = std::io::stdout().flush();
                self.ready_reported = true;
            }
            // The window surface is already live at this point. Keep this
            // first paint deliberately empty: building fonts and even a
            // one-label egui tree adds work before the native window can
            // become visible. The useful loading UI follows on the next
            // update, outside the launch-critical path.
            context.request_repaint();
            return;
        }

        if !self.fonts_initialized {
            trim_font_families(context);
            self.fonts_initialized = true;
        }

        if !self.load_started {
            if let Some(path) = self.path.take() {
                let pending = Arc::new(Mutex::new(None));
                let worker_pending = Arc::clone(&pending);
                std::thread::spawn(move || {
                    let result = Reader::open_viewport(path).map_err(|error| error.to_string());
                    if let Ok(mut slot) = worker_pending.lock() {
                        *slot = Some(result);
                    }
                });
                self.pending = Some(pending);
                self.load_started = true;
            }
        }
        if let Some(pending) = &self.pending {
            let result = pending.lock().ok().and_then(|mut slot| slot.take());
            if let Some(result) = result {
                match result {
                    Ok(viewport) => self.viewport = Some(viewport),
                    Err(error) => self.error = Some(error),
                }
                self.pending = None;
                context.request_repaint();
            }
        }

        if !self.native_title_set {
            if let Some(viewport) = &self.viewport {
                context.send_viewport_cmd(eframe::egui::ViewportCommand::Title(format!(
                    "BlazePDF — {}",
                    viewport.title
                )));
                self.native_title_set = true;
            }
        }

        if self.minimal_startup && self.pending.is_some() {
            eframe::egui::CentralPanel::default().show(context, |ui| {
                ui.label("Loading first page…");
            });
            return;
        }
        eframe::egui::TopBottomPanel::top("toolbar").show(context, |ui| {
            ui.horizontal(|ui| {
                ui.heading("BlazePDF");
                ui.separator();
                ui.label(
                    self.viewport
                        .as_ref()
                        .map(|viewport| viewport.title.as_str())
                        .unwrap_or("Loading first page…"),
                );
                if self.error.is_some() {
                    ui.colored_label(eframe::egui::Color32::RED, "Could not open document");
                } else if self
                    .viewport
                    .as_ref()
                    .is_some_and(|viewport| viewport.page.requires_raster)
                {
                    ui.colored_label(
                        eframe::egui::Color32::YELLOW,
                        "Raster page queued for rendering",
                    );
                } else {
                    ui.colored_label(eframe::egui::Color32::LIGHT_GREEN, "Text layer ready");
                }
            });
        });
        eframe::egui::CentralPanel::default().show(context, |ui| {
            eframe::egui::ScrollArea::vertical().show(ui, |ui| {
                let Some(viewport) = &self.viewport else {
                    ui.label("Loading first page…");
                    return;
                };
                if viewport.page.requires_raster {
                    ui.label("This page has no extractable text layer.");
                    if let Some(error) = &self.error {
                        ui.label(error);
                    } else if viewport.page.text.is_empty() {
                        ui.label("Loading first page…");
                    }
                } else {
                    ui.label(&viewport.page.text);
                }
            });
        });
    }
}

fn main() -> eframe::Result {
    // The benchmark shell measures time to a visible top-level window, not
    // time to initialise a GPU renderer. Keep that path native and tiny;
    // normal launches retain the full eframe viewport below.
    #[cfg(windows)]
    if std::env::var_os("BLAZEPDF_BENCHMARK_SHELL_ONLY").is_some() {
        return run_native_benchmark_shell();
    }

    let path = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .expect("usage: blazepdf-window <document.pdf>");
    let renderer = if std::env::var_os("BLAZEPDF_RENDERER").as_deref()
        == Some(std::ffi::OsStr::new("wgpu"))
    {
        #[cfg(feature = "desktop-wgpu")]
        {
            eframe::Renderer::Wgpu
        }
        #[cfg(not(feature = "desktop-wgpu"))]
        {
            eprintln!("BLAZEPDF_RENDERER=wgpu requested, but this binary was not built with desktop-wgpu; using glow");
            eframe::Renderer::Glow
        }
    } else {
        eframe::Renderer::Glow
    };
    let benchmark_shell_only = std::env::var_os("BLAZEPDF_BENCHMARK_SHELL_ONLY").is_some();
    let viewport = eframe::egui::ViewportBuilder::default()
        .with_visible(true)
        .with_inner_size(if benchmark_shell_only {
            [800.0, 600.0]
        } else {
            [1000.0, 760.0]
        });
    let viewport = if benchmark_shell_only {
        // Avoid eframe's embedded icon decode/upload in the benchmark-only
        // shell. Normal launches retain eframe's default icon.
        viewport.with_icon(eframe::egui::IconData::default())
    } else {
        viewport
    };
    eframe::run_native(
        "BlazePDF",
        eframe::NativeOptions {
            vsync: false,
            multisampling: 0,
            depth_buffer: 0,
            stencil_buffer: 0,
            hardware_acceleration: eframe::HardwareAcceleration::Preferred,
            renderer,
            run_and_return: false,
            centered: false,
            dithering: false,
            persist_window: false,
            persistence_path: None,
            viewport,
            ..Default::default()
        },
        Box::new(|_context| {
            Ok(Box::new(BlazeWindow {
                viewport: None,
                pending: None,
                path: Some(path),
                ready_reported: false,
                first_frame_rendered: false,
                load_started: false,
                native_title_set: false,
                benchmark_ready: std::env::var_os("BLAZEPDF_BENCHMARK_READY").is_some(),
                minimal_startup: std::env::var_os("BLAZEPDF_BENCHMARK_MINIMAL").is_some(),
                fonts_initialized: false,
                error: None,
            }))
        }),
    )
}

#[cfg(windows)]
fn run_native_benchmark_shell() -> eframe::Result {
    use std::ptr::{null, null_mut};
    use windows_sys::Win32::Foundation::{HINSTANCE, HWND, LPARAM, LRESULT, WPARAM};
    use windows_sys::Win32::Graphics::Gdi::UpdateWindow;
    use windows_sys::Win32::System::LibraryLoader::GetModuleHandleW;
    use windows_sys::Win32::UI::WindowsAndMessaging::{
        CreateWindowExW, DefWindowProcW, DispatchMessageW, GetMessageW, PostQuitMessage,
        RegisterClassW, ShowWindow, TranslateMessage, CW_USEDEFAULT, MSG, SW_SHOW, WM_DESTROY,
        WNDCLASSW, WS_OVERLAPPEDWINDOW,
    };

    const CLASS_NAME: &[u16] = &[
        b'B' as u16,
        b'l' as u16,
        b'a' as u16,
        b'z' as u16,
        b'e' as u16,
        b'P' as u16,
        b'D' as u16,
        b'F' as u16,
        0,
    ];
    const TITLE: &[u16] = &[
        b'B' as u16,
        b'l' as u16,
        b'a' as u16,
        b'z' as u16,
        b'e' as u16,
        b'P' as u16,
        b'D' as u16,
        b'F' as u16,
        0,
    ];

    unsafe extern "system" fn window_proc(
        hwnd: HWND,
        message: u32,
        w_param: WPARAM,
        l_param: LPARAM,
    ) -> LRESULT {
        if message == WM_DESTROY {
            PostQuitMessage(0);
            return 0;
        }
        DefWindowProcW(hwnd, message, w_param, l_param)
    }

    unsafe {
        let instance: HINSTANCE = GetModuleHandleW(null());
        let window_class = WNDCLASSW {
            style: 0,
            lpfnWndProc: Some(window_proc),
            cbClsExtra: 0,
            cbWndExtra: 0,
            hInstance: instance,
            hIcon: null_mut(),
            hCursor: null_mut(),
            hbrBackground: null_mut(),
            lpszMenuName: null(),
            lpszClassName: CLASS_NAME.as_ptr(),
        };
        if RegisterClassW(&window_class) == 0 {
            return Err(eframe::Error::AppCreation("RegisterClassW failed".into()));
        }
        let hwnd = CreateWindowExW(
            0,
            CLASS_NAME.as_ptr(),
            TITLE.as_ptr(),
            WS_OVERLAPPEDWINDOW,
            CW_USEDEFAULT,
            CW_USEDEFAULT,
            800,
            600,
            null_mut(),
            null_mut(),
            instance,
            std::ptr::null(),
        );
        if hwnd == null_mut() {
            return Err(eframe::Error::AppCreation("CreateWindowExW failed".into()));
        }
        ShowWindow(hwnd, SW_SHOW);
        UpdateWindow(hwnd);
        println!("BLAZEPDF_FIRST_FRAME_READY");
        let _ = std::io::stdout().flush();

        let mut message = MSG {
            hwnd: null_mut(),
            message: 0,
            wParam: 0,
            lParam: 0,
            time: 0,
            pt: windows_sys::Win32::Foundation::POINT { x: 0, y: 0 },
        };
        while GetMessageW(&mut message, null_mut(), 0, 0) > 0 {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
    }
    Ok(())
}

/// Keep only the text faces the viewport actually draws with.
///
/// egui's default set also carries two emoji faces, and every face in the
/// set is parsed before the first frame can be laid out. A PDF text layer
/// renders in the proportional and monospace faces; the emoji faces cost
/// startup and buy nothing, so they are dropped here rather than by turning
/// off `default_fonts`, which would leave egui with no font at all.
fn trim_font_families(context: &eframe::egui::Context) {
    use eframe::egui::FontFamily;

    static FONTS: OnceLock<eframe::egui::FontDefinitions> = OnceLock::new();
    let fonts = FONTS.get_or_init(|| {
        let mut fonts = eframe::egui::FontDefinitions::default();
        let kept: Vec<String> = fonts
            .families
            .get(&FontFamily::Proportional)
            .into_iter()
            .chain(fonts.families.get(&FontFamily::Monospace))
            .flatten()
            .take(1)
            .cloned()
            .collect();
        let Some(primary) = kept.first().cloned() else {
            return fonts;
        };
        let monospace = fonts
            .families
            .get(&FontFamily::Monospace)
            .and_then(|names| names.first())
            .cloned()
            .unwrap_or_else(|| primary.clone());

        fonts
            .families
            .insert(FontFamily::Proportional, vec![primary.clone()]);
        fonts
            .families
            .insert(FontFamily::Monospace, vec![monospace.clone()]);
        fonts
            .font_data
            .retain(|name, _| *name == primary || *name == monospace);
        fonts
    });
    context.set_fonts(fonts.clone());
}
