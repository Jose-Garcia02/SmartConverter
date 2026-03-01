"""
doc_engine.py — Motor de conversión para documentos ofimáticos y PDF.

- office_to_pdf(): LibreOffice en modo headless.
- pdf_to_word():   pdf2docx nativo en Python.
- Funciones auxiliares para otros formatos ofimáticos.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Formatos soportados
# ---------------------------------------------------------------------------
OFFICE_FORMATS = {"doc", "docx", "odt", "xls", "xlsx", "ods", "ppt", "pptx", "odp"}
PDF_FORMAT = "pdf"
WORD_FORMATS = {"doc", "docx"}

SUPPORTED_DOC_FORMATS = OFFICE_FORMATS | {PDF_FORMAT}


# ---------------------------------------------------------------------------
# Resultado de conversión
# ---------------------------------------------------------------------------
@dataclass
class DocConversionResult:
    """Resultado de una operación de conversión de documentos."""
    input_path: Path
    output_path: Path | None = None
    success: bool = False
    error_message: str = ""


# ---------------------------------------------------------------------------
# Motor de documentos
# ---------------------------------------------------------------------------
class DocEngine:
    """Ejecuta conversiones de documentos vía LibreOffice headless y pdf2docx."""

    def __init__(self) -> None:
        self._soffice = shutil.which("soffice")
        if not self._soffice:
            logger.warning("LibreOffice (soffice) no encontrado en PATH.")

    # -- API pública --------------------------------------------------------
    def convert(self, input_path: Path, output_format: str) -> DocConversionResult:
        """Punto de entrada: detecta tipo de conversión y la ejecuta."""
        input_path = Path(input_path)
        ext_in = input_path.suffix.lower().lstrip(".")
        ext_out = output_format.lower().lstrip(".")

        # Ofimática → PDF
        if ext_in in OFFICE_FORMATS and ext_out == PDF_FORMAT:
            return self.office_to_pdf(input_path)

        # PDF → Word
        if ext_in == PDF_FORMAT and ext_out in WORD_FORMATS:
            return self.pdf_to_word(input_path, ext_out)

        # Ofimática → Ofimática (vía LibreOffice)
        if ext_in in OFFICE_FORMATS and ext_out in OFFICE_FORMATS:
            return self._libre_convert(input_path, ext_out)

        return DocConversionResult(
            input_path=input_path,
            success=False,
            error_message=f"Conversión no soportada: .{ext_in} → .{ext_out}",
        )

    # -- LibreOffice headless → PDF -----------------------------------------
    def office_to_pdf(self, input_path: Path) -> DocConversionResult:
        """Convierte un documento ofimático a PDF usando LibreOffice headless."""
        if not self._soffice:
            return DocConversionResult(
                input_path=input_path,
                success=False,
                error_message="LibreOffice no está instalado.",
            )

        output_dir = input_path.parent
        cmd = [
            self._soffice,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(input_path),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            expected_output = output_dir / f"{input_path.stem}.pdf"
            if proc.returncode == 0 and expected_output.exists():
                logger.info("Documento convertido a PDF: %s", expected_output)
                return DocConversionResult(
                    input_path=input_path,
                    output_path=expected_output,
                    success=True,
                )
            else:
                msg = proc.stderr or f"Código de salida: {proc.returncode}"
                logger.error("Error en office_to_pdf: %s", msg)
                return DocConversionResult(input_path=input_path, success=False, error_message=msg)
        except subprocess.TimeoutExpired:
            msg = f"Timeout al convertir {input_path}"
            logger.error(msg)
            return DocConversionResult(input_path=input_path, success=False, error_message=msg)
        except Exception as exc:  # noqa: BLE001
            msg = f"Error inesperado: {exc}"
            logger.error(msg)
            return DocConversionResult(input_path=input_path, success=False, error_message=msg)

    # -- pdf2docx: PDF → Word -----------------------------------------------
    @staticmethod
    def pdf_to_word(input_path: Path, output_ext: str = "docx") -> DocConversionResult:
        """Convierte un PDF a Word (.docx) usando pdf2docx."""
        try:
            from pdf2docx import Converter  # importación perezosa
        except ImportError:
            return DocConversionResult(
                input_path=input_path,
                success=False,
                error_message="pdf2docx no está instalado. Ejecuta: pip install pdf2docx",
            )

        output_path = input_path.with_suffix(f".{output_ext}")
        try:
            cv = Converter(str(input_path))
            cv.convert(str(output_path))  # type: ignore[reportUnknownMemberType]
            cv.close()

            if output_path.exists():
                logger.info("PDF convertido a Word: %s", output_path)
                return DocConversionResult(
                    input_path=input_path,
                    output_path=output_path,
                    success=True,
                )
            else:
                return DocConversionResult(
                    input_path=input_path,
                    success=False,
                    error_message="pdf2docx terminó pero no generó el archivo.",
                )
        except Exception as exc:  # noqa: BLE001
            msg = f"Error en pdf2docx: {exc}"
            logger.error(msg)
            return DocConversionResult(input_path=input_path, success=False, error_message=msg)

    # -- LibreOffice genérico -----------------------------------------------
    def _libre_convert(self, input_path: Path, output_ext: str) -> DocConversionResult:
        """Convierte entre formatos ofimáticos vía LibreOffice headless."""
        if not self._soffice:
            return DocConversionResult(
                input_path=input_path,
                success=False,
                error_message="LibreOffice no está instalado.",
            )

        output_dir = input_path.parent
        cmd = [
            self._soffice,
            "--headless",
            "--convert-to", output_ext,
            "--outdir", str(output_dir),
            str(input_path),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            expected_output = output_dir / f"{input_path.stem}.{output_ext}"
            if proc.returncode == 0 and expected_output.exists():
                logger.info("Documento convertido: %s → %s", input_path, expected_output)
                return DocConversionResult(
                    input_path=input_path,
                    output_path=expected_output,
                    success=True,
                )
            else:
                msg = proc.stderr or f"Código de salida: {proc.returncode}"
                logger.error("Error en _libre_convert: %s", msg)
                return DocConversionResult(input_path=input_path, success=False, error_message=msg)
        except subprocess.TimeoutExpired:
            msg = f"Timeout al convertir {input_path}"
            logger.error(msg)
            return DocConversionResult(input_path=input_path, success=False, error_message=msg)
        except Exception as exc:  # noqa: BLE001
            msg = f"Error inesperado: {exc}"
            logger.error(msg)
            return DocConversionResult(input_path=input_path, success=False, error_message=msg)

    # -- utilidades ---------------------------------------------------------
    @staticmethod
    def supported_output_formats(input_path: Path) -> set[str]:
        """Devuelve formatos de salida válidos para un documento dado."""
        ext = input_path.suffix.lower().lstrip(".")
        if ext in OFFICE_FORMATS:
            return ({PDF_FORMAT} | OFFICE_FORMATS) - {ext}
        if ext == PDF_FORMAT:
            return {"docx"}
        return set()
