# pyright: reportUnknownMemberType=false, reportUnknownParameterType=false
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false, reportReturnType=false
# pyright: reportUntypedBaseClass=false
"""
SmartConverterExt.py — Extensión de Nautilus para Smart Converter.

Añade una opción "Convertir con SmartConverter" al menú contextual
cuando se seleccionan archivos con extensiones compatibles.

Instalación:
    Copiar o enlazar este archivo en:
    ~/.local/share/nautilus-python/extensions/SmartConverterExt.py

Requiere:
    sudo dnf install nautilus-python
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import gi

# Detectar la versión de Nautilus disponible (4.1 en Fedora 43+, 4.0/3.0 en otras)
for _nautilus_ver in ("4.1", "4.0", "3.0"):
    try:
        gi.require_version("Nautilus", _nautilus_ver)
        break
    except ValueError:
        continue

from gi.repository import GObject  # noqa: E402
from gi.repository import Nautilus  # type: ignore[reportUnknownVariableType]  # noqa: E402

# Ruta al lanzador instalado, con fallback al main.py local para desarrollo
_LAUNCHER = os.path.expanduser("~/.local/bin/smart-converter")
_MAIN_SCRIPT = Path(__file__).resolve().parents[1] / "main.py"

def _get_cmd_prefix() -> list[str]:
    """Determina cómo lanzar SmartConverter."""
    if os.path.isfile(_LAUNCHER) and os.access(_LAUNCHER, os.X_OK):
        return [_LAUNCHER]
    return ["python3", str(_MAIN_SCRIPT)]

# Extensiones que activan la opción en el menú contextual
_SUPPORTED_EXTENSIONS = {
    # Audio
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma", ".m4a", ".opus",
    # Video
    ".mp4", ".mkv", ".avi", ".webm", ".mov", ".flv", ".wmv", ".ts",
    # Imágenes
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".svg", ".ico",
    # Documentos
    ".doc", ".docx", ".odt", ".xls", ".xlsx", ".ods",
    ".ppt", ".pptx", ".odp", ".pdf",
}


class SmartConverterMenuProvider(GObject.GObject, Nautilus.MenuProvider):
    """Proveedor de menú contextual para Nautilus."""

    def get_file_items(self, *args: Any) -> list[Nautilus.MenuItem] | None:
        """
        Se llama cuando el usuario hace clic derecho sobre archivos.
        Muestra la opción solo si al menos un archivo tiene extensión soportada.
        """
        # Nautilus 4.x pasa (files,), Nautilus 3.x pasa (window, files)
        files = args[-1] if args else []

        # Filtrar archivos válidos
        valid_paths: list[str] = []
        for file_info in files:
            if file_info.get_uri_scheme() != "file":
                continue
            uri = file_info.get_uri()
            # Decodificar URI a ruta local (maneja %20, acentos, etc.)
            path_str = unquote(uri.replace("file://", ""))
            path = Path(path_str)
            if path.suffix.lower() in _SUPPORTED_EXTENSIONS:
                valid_paths.append(str(path))

        if not valid_paths:
            return None

        # Crear item de menú
        item = Nautilus.MenuItem(
            name="SmartConverter::convert",
            label=f"Convertir con SmartConverter ({len(valid_paths)} archivo{'s' if len(valid_paths) > 1 else ''})",
            tip="Abrir Smart Converter para convertir los archivos seleccionados",
        )
        item.connect("activate", self._on_activate, valid_paths)
        return [item]

    def _on_activate(
        self,
        _menu_item: Nautilus.MenuItem,
        file_paths: list[str],
    ) -> None:
        """Lanza Smart Converter en modo GUI con los archivos seleccionados."""
        cmd = _get_cmd_prefix() + ["--gui", "--input"] + file_paths

        subprocess.Popen(
            cmd,
            start_new_session=True,  # No bloquear Nautilus
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
