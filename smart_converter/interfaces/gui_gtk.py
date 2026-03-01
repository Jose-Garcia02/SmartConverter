"""
gui_gtk.py — Interfaz gráfica GTK4 para Smart Converter.

Implementa tres ventanas compactas y flotantes:
  1. Ventana de selección de archivos (cuando no se pasan por CLI).
  2. Ventana de selección de formato de salida.
  3. Ventana de progreso de conversión.

Diseñadas para funcionar correctamente tanto en escritorios convencionales
(GNOME, KDE) como en tiling window managers (niri, sway, Hyprland).
Usa GLib.idle_add() para actualizar la UI de forma segura desde hilos.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from smart_converter.core.orchestrator import BatchResult, Orchestrator, classify_file

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Icono de la aplicación
# ---------------------------------------------------------------------------
_ICON_NAME = "com.smartconverter.app"

# Rutas raíz de temas de iconos adicionales (para modo desarrollo)
# GTK espera la estructura: {raíz}/hicolor/{tamaño}/apps/{nombre}.png
_EXTRA_ICON_THEME_ROOTS = [
    Path.home() / ".local/share/icons",  # Instalación del usuario
]


def _load_app_icon() -> str:
    """Intenta cargar el icono de la app desde el tema de iconos GTK."""
    display = Gdk.Display.get_default()
    if display is None:
        return "applications-multimedia"

    theme = Gtk.IconTheme.get_for_display(display)

    # Añadir rutas de búsqueda extra (la de usuario suele estar, pero aseguramos)
    for root in _EXTRA_ICON_THEME_ROOTS:
        if root.exists():
            theme.add_search_path(str(root))

    # El icono ya debería estar disponible si se instaló con install.sh
    # (~/.local/share/icons/hicolor/{tamaño}/apps/com.smartconverter.app.png)
    if theme.has_icon(_ICON_NAME):
        return _ICON_NAME

    # Fallback: buscar un icono genérico del sistema
    for fallback in ("multimedia-photo-manager", "applications-multimedia",
                     "preferences-desktop-multimedia", "image-x-generic"):
        if theme.has_icon(fallback):
            return fallback

    return "applications-multimedia"


def _setup_floating_window(window: Adw.ApplicationWindow, width: int, height: int) -> None:
    """Configura una ventana para que sea compacta y flotante en tiling WMs."""
    window.set_default_size(width, height)
    window.set_resizable(False)  # Señal para tiling WMs → ventana flotante
    window.set_size_request(width, height)  # Tamaño mínimo = tamaño fijo


# ---------------------------------------------------------------------------
# Aplicación principal
# ---------------------------------------------------------------------------
class SmartConverterApp(Adw.Application):
    """Aplicación GTK4/Adwaita de Smart Converter."""

    def __init__(self, files: list[Path] | None = None) -> None:
        super().__init__(application_id="com.smartconverter.app")
        self.files = files or []
        self.connect("activate", self._on_activate)

    def _on_activate(self, app: Adw.Application) -> None:
        # Cargar icono
        icon_name = _load_app_icon()

        if self.files:
            win = FormatSelectionWindow(app=app, files=self.files, icon_name=icon_name)
        else:
            win = FileChooserWindow(app=app, icon_name=icon_name)
        win.present()


# ---------------------------------------------------------------------------
# Ventana: Selector de archivos (cuando no se pasan por argumento)
# ---------------------------------------------------------------------------
class FileChooserWindow(Adw.ApplicationWindow):
    """Ventana compacta para elegir archivos si no se proporcionaron vía CLI."""

    def __init__(self, app: Adw.Application, icon_name: str = "") -> None:
        super().__init__(application=app, title="Smart Converter")
        _setup_floating_window(self, 340, 180)
        if icon_name:
            self.set_icon_name(icon_name)

        # HeaderBar compacta
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)

        # Contenido
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.append(header)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        inner.set_margin_top(16)
        inner.set_margin_bottom(16)
        inner.set_margin_start(20)
        inner.set_margin_end(20)
        inner.set_valign(Gtk.Align.CENTER)

        icon_img = Gtk.Image.new_from_icon_name(icon_name or "document-open-symbolic")
        icon_img.set_pixel_size(36)
        inner.append(icon_img)

        label = Gtk.Label(label="Selecciona archivos para convertir")
        label.add_css_class("title-4")
        inner.append(label)

        btn = Gtk.Button(label="Abrir archivos…")
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.connect("clicked", self._on_open_clicked)
        inner.append(btn)

        content.append(inner)
        self.set_content(content)

    def _on_open_clicked(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar archivos")
        # Permitir múltiples archivos
        dialog.open_multiple(self, None, self._on_files_selected)

    def _on_files_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file_list = dialog.open_multiple_finish(result)
            paths: list[Path] = []
            for i in range(file_list.get_n_items()):
                item = file_list.get_item(i)
                if isinstance(item, Gio.File):
                    file_path = item.get_path()
                    if file_path:
                        paths.append(Path(file_path))
            if paths:
                app = self.get_application()
                assert isinstance(app, Adw.Application)
                icon = self.get_icon_name() or ""
                win = FormatSelectionWindow(app=app, files=paths, icon_name=icon)
                win.present()
                self.close()
        except GLib.Error as e:
            logger.debug("Diálogo cancelado: %s", e.message)


# ---------------------------------------------------------------------------
# Ventana: Selección de formato de salida
# ---------------------------------------------------------------------------
class FormatSelectionWindow(Adw.ApplicationWindow):
    """Ventana compacta que muestra los archivos y permite elegir formato."""

    def __init__(self, app: Adw.Application, files: list[Path], icon_name: str = "") -> None:
        super().__init__(application=app, title="Smart Converter")
        self.files = files
        self._icon_name = icon_name
        self._orchestrator = Orchestrator()

        if icon_name:
            self.set_icon_name(icon_name)

        # -- Calcular formatos comunes disponibles --------------------------
        format_sets = [self._orchestrator.supported_output_formats(f) for f in files]
        self._common_formats: list[str]
        if format_sets:
            first, *rest = format_sets
            common: set[str] = first.intersection(*rest) if rest else first
            self._common_formats = sorted(common)
        else:
            self._common_formats = []

        # Ajustar altura según la cantidad de archivos (compacta)
        n_files = min(len(files), 5)
        height = 220 + n_files * 18
        _setup_floating_window(self, 360, min(height, 380))

        self._build_ui()

    def _build_ui(self) -> None:
        # HeaderBar
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Elegir formato"))

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.append(header)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        inner.set_margin_top(12)
        inner.set_margin_bottom(16)
        inner.set_margin_start(16)
        inner.set_margin_end(16)

        # Resumen de archivos (compacto)
        n = len(self.files)
        category = classify_file(self.files[0]) if self.files else "archivo"
        summary_text = f"{n} archivo{'s' if n > 1 else ''}  •  {category}"
        summary = Gtk.Label(label=summary_text)
        summary.add_css_class("title-4")
        inner.append(summary)

        # Lista de archivos (máx 5, nombres truncados)
        names: list[str] = []
        for f in self.files[:5]:
            name = f.name
            if len(name) > 32:
                name = name[:29] + "…"
            names.append(f"  {name}")
        if n > 5:
            names.append(f"  … y {n - 5} más")
        files_label = Gtk.Label(label="\n".join(names))
        files_label.set_xalign(0)
        files_label.add_css_class("dim-label")
        files_label.add_css_class("caption")
        inner.append(files_label)

        inner.append(Gtk.Separator())

        # Selector de formato — fila horizontal compacta
        fmt_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fmt_row.set_halign(Gtk.Align.CENTER)
        fmt_label = Gtk.Label(label="Formato:")
        fmt_row.append(fmt_label)

        self._format_dropdown = Gtk.DropDown.new_from_strings(
            self._common_formats if self._common_formats else ["(sin formatos)"]
        )
        self._format_dropdown.set_hexpand(False)
        fmt_row.append(self._format_dropdown)
        inner.append(fmt_row)

        # Botón convertir
        convert_btn = Gtk.Button(label="Convertir")
        convert_btn.add_css_class("suggested-action")
        convert_btn.add_css_class("pill")
        convert_btn.set_halign(Gtk.Align.CENTER)
        convert_btn.set_sensitive(bool(self._common_formats))
        convert_btn.connect("clicked", self._on_convert)
        inner.append(convert_btn)

        main_box.append(inner)
        self.set_content(main_box)

    def _on_convert(self, _button: Gtk.Button) -> None:
        idx = self._format_dropdown.get_selected()
        if idx < 0 or idx >= len(self._common_formats):
            return
        output_format: str = self._common_formats[idx]
        app = self.get_application()
        assert isinstance(app, Adw.Application)
        win = ProgressWindow(
            app=app,
            files=self.files,
            output_format=output_format,
            icon_name=self._icon_name,
        )
        win.present()
        self.close()


# ---------------------------------------------------------------------------
# Ventana: Progreso de conversión
# ---------------------------------------------------------------------------
class ProgressWindow(Adw.ApplicationWindow):
    """Ventana compacta que muestra el progreso de conversión."""

    def __init__(
        self,
        app: Adw.Application,
        files: list[Path],
        output_format: str,
        icon_name: str = "",
    ) -> None:
        super().__init__(application=app, title="Convirtiendo…")
        _setup_floating_window(self, 340, 160)
        if icon_name:
            self.set_icon_name(icon_name)

        self.files = files
        self.output_format = output_format
        self._orchestrator = Orchestrator()

        self._build_ui()
        threading.Thread(target=self._run_conversion, daemon=True).start()

    def _build_ui(self) -> None:
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Convirtiendo…"))

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.append(header)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        inner.set_margin_top(12)
        inner.set_margin_bottom(16)
        inner.set_margin_start(16)
        inner.set_margin_end(16)
        inner.set_valign(Gtk.Align.CENTER)

        self._status_label = Gtk.Label(label="Iniciando…")
        self._status_label.add_css_class("title-4")
        inner.append(self._status_label)

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_show_text(True)
        inner.append(self._progress_bar)

        self._detail_label = Gtk.Label(label=f"{len(self.files)} archivo(s) → .{self.output_format}")
        self._detail_label.add_css_class("dim-label")
        self._detail_label.add_css_class("caption")
        inner.append(self._detail_label)

        main_box.append(inner)
        self.set_content(main_box)

    def _run_conversion(self) -> None:
        """Ejecuta la conversión en un hilo de fondo, actualiza la UI vía GLib.idle_add."""

        def on_progress(completed: int, total: int) -> None:
            fraction = completed / total if total > 0 else 0
            GLib.idle_add(self._update_progress, fraction, completed, total)

        batch = self._orchestrator.convert_batch(
            self.files, self.output_format, on_progress=on_progress
        )
        GLib.idle_add(self._on_finished, batch)

    def _update_progress(self, fraction: float, completed: int, total: int) -> bool:
        self._progress_bar.set_fraction(fraction)
        self._progress_bar.set_text(f"{completed}/{total}")
        self._status_label.set_label(f"Convirtiendo… {completed}/{total}")
        return False

    def _on_finished(self, batch: BatchResult) -> bool:
        self._progress_bar.set_fraction(1.0)
        self._progress_bar.set_text("Listo")
        if batch.all_ok:
            self._status_label.set_label(f"✅ {batch.successful} convertido(s)")
            self._detail_label.set_label("Conversión completada exitosamente")
        else:
            self._status_label.set_label("⚠️ Terminado con errores")
            failed = [r.input_path.name for r in batch.results if not r.success]
            detail = f"✅ {batch.successful}  ❌ {batch.failed}"
            if failed:
                detail += "\n" + "\n".join(f"  • {n[:28]}" for n in failed[:3])
            self._detail_label.set_label(detail)
        return False


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def run_gui(files: list[Path] | None = None) -> None:
    """Lanza la aplicación GTK4."""
    app = SmartConverterApp(files=files)
    app.run(None)
