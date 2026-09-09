#!/usr/bin/env python3
"""Regenera o relatório demo a partir do fixture sintético."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from diskaudit.cli import main as cli_main  # noqa: E402

DEFAULT_CSV = _ROOT / "tests" / "fixtures" / "sample.csv"
DEFAULT_OUT = _ROOT / "examples" / "demo_report.html"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera examples/demo_report.html a partir do fixture anonymizado"
    )
    parser.add_argument(
        "csv",
        nargs="?",
        default=str(DEFAULT_CSV),
        help=f"CSV de entrada (padrão: {DEFAULT_CSV.relative_to(_ROOT)})",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_OUT),
        help=f"HTML de saída (padrão: {DEFAULT_OUT.relative_to(_ROOT)})",
    )
    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = (_ROOT / csv_path).resolve()
    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = (_ROOT / out_path).resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    return cli_main([str(csv_path), "-o", str(out_path)])


if __name__ == "__main__":
    sys.exit(main())
