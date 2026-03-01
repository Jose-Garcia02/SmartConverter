"""
media_engine.py — Motor de conversión para audio, video e imágenes.

Envuelve FFmpeg (audio/video) e ImageMagick (imágenes) usando subprocess.
Cada función recibe rutas de entrada/salida y devuelve un resultado tipado.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Formatos soportados (se amplían según necesidad)
# ---------------------------------------------------------------------------
AUDIO_FORMATS = {"mp3", "wav", "ogg", "flac", "aac", "wma", "m4a", "opus"}
VIDEO_FORMATS = {"mp4", "mkv", "avi", "webm", "mov", "flv", "wmv", "ts"}
IMAGE_FORMATS = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "svg", "ico"}

SUPPORTED_FORMATS = AUDIO_FORMATS | VIDEO_FORMATS | IMAGE_FORMATS


# ---------------------------------------------------------------------------
# Resultado de conversión
# ---------------------------------------------------------------------------
@dataclass
class ConversionResult:
    """Resultado de una operación de conversión individual."""
    input_path: Path
    output_path: Path | None = None
    success: bool = False
    error_message: str = ""
    stderr_output: str = ""


# ---------------------------------------------------------------------------
# Motor de medios
# ---------------------------------------------------------------------------
class MediaEngine:
    """Ejecuta conversiones de audio, video e imágenes vía FFmpeg / ImageMagick."""

    def __init__(self) -> None:
        self._ffmpeg = shutil.which("ffmpeg")
        # ImageMagick 7 usa 'magick'; fallback a 'convert' para IM 6
        self._magick = shutil.which("magick") or shutil.which("convert")
        self._check_dependencies()

    # -- verificación -------------------------------------------------------
    def _check_dependencies(self) -> None:
        if not self._ffmpeg:
            logger.warning("FFmpeg no encontrado en PATH. Las conversiones de audio/video fallarán.")
        if not self._magick:
            logger.warning("ImageMagick no encontrado en PATH. Las conversiones de imagen fallarán.")

    # -- API pública --------------------------------------------------------
    def convert(self, input_path: Path, output_format: str) -> ConversionResult:
        """Punto de entrada principal: detecta tipo y enruta al conversor adecuado."""
        input_path = Path(input_path)
        ext = output_format.lower().lstrip(".")

        if ext in AUDIO_FORMATS | VIDEO_FORMATS:
            return self._convert_media(input_path, ext)
        elif ext in IMAGE_FORMATS:
            return self._convert_image(input_path, ext)
        else:
            return ConversionResult(
                input_path=input_path,
                success=False,
                error_message=f"Formato de salida no soportado: {ext}",
            )

    # -- conversión FFmpeg --------------------------------------------------
    def _convert_media(self, input_path: Path, output_ext: str) -> ConversionResult:
        """Convierte audio/video con FFmpeg."""
        if not self._ffmpeg:
            return ConversionResult(
                input_path=input_path, success=False,
                error_message="FFmpeg no está instalado.",
            )
        output_path = input_path.with_suffix(f".{output_ext}")
        cmd: list[str] = [
            self._ffmpeg,
            "-i", str(input_path),
            "-y",                       # sobre-escribir sin preguntar
            str(output_path),
        ]
        return self._run_command(cmd, input_path, output_path)

    # -- conversión ImageMagick ---------------------------------------------
    def _convert_image(self, input_path: Path, output_ext: str) -> ConversionResult:
        """Convierte imágenes con ImageMagick."""
        if not self._magick:
            return ConversionResult(
                input_path=input_path, success=False,
                error_message="ImageMagick no está instalado.",
            )
        output_path = input_path.with_suffix(f".{output_ext}")
        cmd: list[str] = [
            self._magick,
            str(input_path),
            str(output_path),
        ]
        return self._run_command(cmd, input_path, output_path)

    # -- runner genérico ----------------------------------------------------
    @staticmethod
    def _run_command(
        cmd: list[str],
        input_path: Path,
        output_path: Path,
    ) -> ConversionResult:
        """Ejecuta un comando y captura stdout/stderr."""
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,            # 5 min máximo por archivo
            )
            if proc.returncode == 0 and output_path.exists():
                logger.info("Conversión exitosa: %s -> %s", input_path, output_path)
                return ConversionResult(
                    input_path=input_path,
                    output_path=output_path,
                    success=True,
                    stderr_output=proc.stderr,
                )
            else:
                logger.error("Error convirtiendo %s: %s", input_path, proc.stderr)
                return ConversionResult(
                    input_path=input_path,
                    success=False,
                    error_message=proc.stderr or f"Código de salida: {proc.returncode}",
                    stderr_output=proc.stderr,
                )
        except FileNotFoundError as exc:
            msg = f"Ejecutable no encontrado: {exc}"
            logger.error(msg)
            return ConversionResult(input_path=input_path, success=False, error_message=msg)
        except subprocess.TimeoutExpired:
            msg = f"Timeout al convertir {input_path}"
            logger.error(msg)
            return ConversionResult(input_path=input_path, success=False, error_message=msg)
        except Exception as exc:  # noqa: BLE001
            msg = f"Error inesperado: {exc}"
            logger.error(msg)
            return ConversionResult(input_path=input_path, success=False, error_message=msg)

    # -- utilidades ---------------------------------------------------------
    @staticmethod
    def supported_output_formats(input_path: Path) -> set[str]:
        """Devuelve formatos de salida válidos según la extensión de entrada."""
        ext = input_path.suffix.lower().lstrip(".")
        if ext in AUDIO_FORMATS:
            return AUDIO_FORMATS - {ext}
        if ext in VIDEO_FORMATS:
            return VIDEO_FORMATS - {ext}
        if ext in IMAGE_FORMATS:
            return IMAGE_FORMATS - {ext}
        return set()
