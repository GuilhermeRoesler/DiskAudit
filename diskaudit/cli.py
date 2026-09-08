"""Interface de linha de comando."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from diskaudit.analyze import analyze, load_csv
from diskaudit.render import DEFAULT_TEMPLATE_DIR, render_html
from diskaudit.util import log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoria de disco a partir de CSV do WinDirStat")
    parser.add_argument("csv", nargs="?", default="disk.csv", help="Caminho do CSV exportado")
    parser.add_argument("-o", "--output", default="disk_report.html", help="Arquivo HTML de saída")
    parser.add_argument("-t", "--template-dir", default=None, help="Diretório do template")
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = cwd / csv_path
    if not csv_path.exists():
        log(f"Erro: arquivo não encontrado: {csv_path}")
        return 1

    template_dir = Path(args.template_dir) if args.template_dir else DEFAULT_TEMPLATE_DIR
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = cwd / output_path

    frames = load_csv(csv_path)
    log("Analisando…")
    data, root, user = analyze(frames)
    log(f"  Raiz: {root} | Perfil: {user or 'não detectado'}")
    log(f"  {data['root_gb']:.1f} GB | {len(data['candidates'])} candidatos")

    render_html(data, root, user, template_dir, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
