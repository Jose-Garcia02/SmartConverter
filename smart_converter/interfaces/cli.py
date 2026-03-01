"""
cli.py — Interfaz de línea de comandos para Smart Converter.

Uso:
    smart-converter --input archivo1.mp4 archivo2.docx --to mp3
    smart-converter --input *.png --to webp --verbose
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tqdm import tqdm

from smart_converter.core.orchestrator import Orchestrator, classify_file

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos."""
    parser = argparse.ArgumentParser(
        prog="smart-converter",
        description="Smart Converter — Convierte archivos multimedia y documentos desde la terminal.",
        epilog="Ejemplo: smart-converter --input video.mp4 foto.png --to webp",
    )
    parser.add_argument(
        "-i", "--input",
        nargs="+",
        required=True,
        type=Path,
        help="Archivos de entrada a convertir.",
        metavar="ARCHIVO",
    )
    parser.add_argument(
        "-t", "--to",
        required=True,
        type=str,
        help="Formato de salida (ej: mp3, pdf, webp, docx).",
        metavar="FORMATO",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Número de hilos simultáneos (por defecto: 4).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Activar mensajes detallados de depuración.",
    )
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    """Ejecuta la CLI. Devuelve 0 si todo OK, 1 si hubo errores."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # -- configurar logging -------------------------------------------------
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )

    # -- validar archivos de entrada ----------------------------------------
    valid_files: list[Path] = []
    for fpath in args.input:
        if not fpath.exists():
            logger.error("Archivo no encontrado: %s", fpath)
        elif not fpath.is_file():
            logger.error("No es un archivo regular: %s", fpath)
        else:
            valid_files.append(fpath.resolve())

    if not valid_files:
        logger.error("No se encontraron archivos válidos para convertir.")
        return 1

    output_format = args.to.lower().lstrip(".")

    # -- mostrar resumen ----------------------------------------------------
    print(f"\n📂 Archivos a convertir: {len(valid_files)}")
    print(f"🎯 Formato de salida:   .{output_format}")
    print(f"⚡ Hilos:               {args.workers}\n")

    if args.verbose:
        orch_temp = Orchestrator()
        for f in valid_files:
            cat = classify_file(f)
            fmts = orch_temp.supported_output_formats(f)
            print(f"  {f.name}  [{cat}]  → formatos posibles: {', '.join(sorted(fmts)) or 'ninguno'}")
        print()

    # -- barra de progreso con tqdm -----------------------------------------
    progress_bar = tqdm(
        total=len(valid_files),
        desc="Convirtiendo",
        unit="archivo",
        ncols=80,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    )

    def on_progress(completed: int, total: int) -> None:
        progress_bar.update(1)

    # -- ejecutar conversión ------------------------------------------------
    orchestrator = Orchestrator(max_workers=args.workers)
    batch = orchestrator.convert_batch(valid_files, output_format, on_progress=on_progress)
    progress_bar.close()

    # -- resumen final ------------------------------------------------------
    print(f"\n✅ Exitosas: {batch.successful}/{batch.total}")
    if batch.failed > 0:
        print(f"❌ Fallidas: {batch.failed}/{batch.total}")
        for r in batch.results:
            if not r.success:
                print(f"   • {r.input_path.name}: {r.error_message}")

    return 0 if batch.all_ok else 1


if __name__ == "__main__":
    sys.exit(run_cli())
