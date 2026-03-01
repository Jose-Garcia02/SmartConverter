#!/usr/bin/env python3
"""
main.py — Punto de entrada de Smart Converter.

Enruta a la interfaz CLI o GUI según los argumentos recibidos.

Uso:
    # Modo CLI (por defecto)
    python main.py --input archivo.mp4 --to mp3

    # Modo GUI
    python main.py --gui
    python main.py --gui --input archivo1.docx archivo2.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    """Punto de entrada principal."""
    args = sys.argv[1:]

    # Si se pide GUI explícitamente
    if "--gui" in args:
        args_clean = [a for a in args if a != "--gui"]

        # Extraer archivos si se pasaron con --input / -i
        files: list[Path] = []
        i = 0
        while i < len(args_clean):
            if args_clean[i] in ("--input", "-i"):
                i += 1
                while i < len(args_clean) and not args_clean[i].startswith("-"):
                    files.append(Path(args_clean[i]))
                    i += 1
            else:
                i += 1

        from smart_converter.interfaces.gui_gtk import run_gui
        run_gui(files=files if files else None)
        return 0

    # Modo CLI (por defecto)
    from smart_converter.interfaces.cli import run_cli
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
