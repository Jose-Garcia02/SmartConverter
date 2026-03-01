"""
orchestrator.py — Motor multihilo para conversiones en lote.

Recibe una lista de archivos, los clasifica y los distribuye entre
ThreadPoolExecutor workers. Reporta progreso (0-100%) mediante un callback.
"""

from __future__ import annotations

import logging
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .doc_engine import DocEngine, DocConversionResult, SUPPORTED_DOC_FORMATS
from .media_engine import (
    MediaEngine,
    ConversionResult,
    AUDIO_FORMATS,
    VIDEO_FORMATS,
    IMAGE_FORMATS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tipos de archivo reconocidos
# ---------------------------------------------------------------------------
CATEGORY_AUDIO = "audio"
CATEGORY_VIDEO = "video"
CATEGORY_IMAGE = "image"
CATEGORY_DOCUMENT = "document"
CATEGORY_UNKNOWN = "unknown"


def classify_file(file_path: Path) -> str:
    """Clasifica un archivo por su extensión (con fallback a mimetypes)."""
    ext = file_path.suffix.lower().lstrip(".")

    if ext in AUDIO_FORMATS:
        return CATEGORY_AUDIO
    if ext in VIDEO_FORMATS:
        return CATEGORY_VIDEO
    if ext in IMAGE_FORMATS:
        return CATEGORY_IMAGE
    if ext in SUPPORTED_DOC_FORMATS:
        return CATEGORY_DOCUMENT

    # Fallback: consultar mimetypes del sistema
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        major = mime.split("/")[0]
        if major == "audio":
            return CATEGORY_AUDIO
        if major == "video":
            return CATEGORY_VIDEO
        if major == "image":
            return CATEGORY_IMAGE
        if major in ("application", "text"):
            return CATEGORY_DOCUMENT

    return CATEGORY_UNKNOWN


# ---------------------------------------------------------------------------
# Resultado agregado de un lote
# ---------------------------------------------------------------------------
@dataclass
class BatchResult:
    """Resumen de una conversión en lote."""
    total: int = 0
    successful: int = 0
    failed: int = 0
    results: list[ConversionResult | DocConversionResult] = field(
        default_factory=lambda: list[ConversionResult | DocConversionResult]()
    )

    @property
    def all_ok(self) -> bool:
        return self.failed == 0 and self.total > 0


# Tipo para el callback de progreso: recibe (completados, total)
ProgressCallback = Callable[[int, int], None]


# ---------------------------------------------------------------------------
# Orquestador
# ---------------------------------------------------------------------------
class Orchestrator:
    """Distribuye conversiones entre hilos y reporta progreso."""

    def __init__(self, max_workers: int = 4) -> None:
        self.max_workers = max_workers
        self._media = MediaEngine()
        self._doc = DocEngine()

    # -- API pública --------------------------------------------------------
    def convert_batch(
        self,
        files: list[Path],
        output_format: str,
        on_progress: ProgressCallback | None = None,
    ) -> BatchResult:
        """
        Convierte una lista de archivos al formato indicado, en paralelo.

        Args:
            files: Lista de rutas a convertir.
            output_format: Extensión de salida (sin punto).
            on_progress: Callback opcional (completados, total).

        Returns:
            BatchResult con el resumen completo.
        """
        total = len(files)
        batch = BatchResult(total=total)
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_map = {
                pool.submit(self._convert_single, fpath, output_format): fpath
                for fpath in files
            }

            for future in as_completed(future_map):
                fpath = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001
                    logger.error("Excepción en hilo para %s: %s", fpath, exc)
                    result = ConversionResult(
                        input_path=fpath,
                        success=False,
                        error_message=str(exc),
                    )

                batch.results.append(result)
                if result.success:
                    batch.successful += 1
                else:
                    batch.failed += 1

                completed += 1
                if on_progress:
                    on_progress(completed, total)

        return batch

    # -- conversión individual ----------------------------------------------
    def _convert_single(
        self,
        file_path: Path,
        output_format: str,
    ) -> ConversionResult | DocConversionResult:
        """Clasifica el archivo y lo envía al motor correspondiente."""
        category = classify_file(file_path)
        logger.debug("Archivo: %s → categoría: %s", file_path, category)

        if category in (CATEGORY_AUDIO, CATEGORY_VIDEO, CATEGORY_IMAGE):
            return self._media.convert(file_path, output_format)
        elif category == CATEGORY_DOCUMENT:
            return self._doc.convert(file_path, output_format)
        else:
            return ConversionResult(
                input_path=file_path,
                success=False,
                error_message=f"Tipo de archivo no reconocido: {file_path.suffix}",
            )

    # -- utilidades ---------------------------------------------------------
    def supported_output_formats(self, file_path: Path) -> set[str]:
        """Formatos de salida disponibles para un archivo dado."""
        category = classify_file(file_path)
        if category in (CATEGORY_AUDIO, CATEGORY_VIDEO, CATEGORY_IMAGE):
            return self._media.supported_output_formats(file_path)
        elif category == CATEGORY_DOCUMENT:
            return self._doc.supported_output_formats(file_path)
        return set()

    @staticmethod
    def progress_percent(completed: int, total: int) -> float:
        """Calcula el porcentaje de progreso (0.0 – 100.0)."""
        if total <= 0:
            return 0.0
        return round((completed / total) * 100, 1)
