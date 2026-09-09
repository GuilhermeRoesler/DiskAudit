#!/usr/bin/env python3
"""Valida export CSV do WinDirStat antes de rodar a auditoria."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from diskaudit.validate import validate


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida CSV exportado pelo WinDirStat")
    parser.add_argument("csv", nargs="?", default="disk.csv", help="Caminho do CSV")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent.parent
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = script_dir / csv_path

    print(f"Validando {csv_path}…", flush=True)
    errors, warnings = validate(csv_path)

    for w in warnings:
        print(f"  AVISO: {w}", flush=True)

    if errors:
        print("FALHOU:", flush=True)
        for e in errors:
            print(f"  ERRO: {e}", flush=True)
        return 1

    print("OK — CSV pronto para disk-audit", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
