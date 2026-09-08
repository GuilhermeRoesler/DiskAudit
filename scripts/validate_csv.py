#!/usr/bin/env python3
"""Valida export CSV do WinDirStat antes de rodar a auditoria."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402

from diskaudit.constants import (  # noqa: E402
    COL_FILES,
    COL_LOGICAL,
    COL_MTIME,
    COL_PATH,
    COL_PHYSICAL,
    COL_SUBDIRS,
)

REQUIRED_COLS = [COL_PATH, COL_FILES, COL_SUBDIRS, COL_PHYSICAL, COL_LOGICAL, COL_MTIME]
INT_COLS = [COL_FILES, COL_SUBDIRS, COL_PHYSICAL, COL_LOGICAL]
ROOT_PATTERN = re.compile(r"^[A-Z]:\\?$")


def validate(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not path.exists():
        return [f"Arquivo não encontrado: {path}"], warnings

    if path.stat().st_size == 0:
        return ["Arquivo CSV vazio."], warnings

    try:
        header = pd.read_csv(path, encoding="utf-8", nrows=0)
    except UnicodeDecodeError:
        errors.append("Encoding inválido — esperado UTF-8.")
        return errors, warnings
    except pd.errors.EmptyDataError:
        return ["Arquivo CSV sem conteúdo."], warnings
    except Exception as exc:
        return [f"Erro ao ler CSV: {exc}"], warnings

    missing = [c for c in REQUIRED_COLS if c not in header.columns]
    if missing:
        errors.append(f"Colunas ausentes: {', '.join(missing)}")
        errors.append(f"Colunas encontradas: {', '.join(header.columns.astype(str))}")
        return errors, warnings

    extra = [c for c in header.columns if c not in REQUIRED_COLS]
    if extra:
        warnings.append(f"Colunas extras (ignoradas): {', '.join(map(str, extra))}")

    try:
        df = pd.read_csv(
            path,
            encoding="utf-8",
            dtype={
                COL_FILES: "int64",
                COL_SUBDIRS: "int64",
                COL_PHYSICAL: "int64",
                COL_LOGICAL: "int64",
            },
        )
    except ValueError as exc:
        errors.append(f"Tipos de coluna inválidos: {exc}")
        return errors, warnings
    except Exception as exc:
        errors.append(f"Erro ao parsear CSV: {exc}")
        return errors, warnings

    if df.empty:
        errors.append("CSV não contém linhas de dados.")
        return errors, warnings

    if df[COL_PATH].isna().any():
        n = int(df[COL_PATH].isna().sum())
        errors.append(f"{n} linha(s) com caminho (Nome) vazio.")

    for col in INT_COLS:
        if (df[col] < 0).any():
            n = int((df[col] < 0).sum())
            warnings.append(f"{n} linha(s) com valor negativo em '{col}'.")

    paths = df[COL_PATH].astype(str).str.replace("/", "\\", regex=False)
    roots = paths[paths.str.match(ROOT_PATTERN, na=False)]
    if roots.empty:
        warnings.append(
            "Nenhuma raiz de unidade detectada (ex.: C:\\). Análise usará fallback por profundidade."
        )
    else:
        root = roots.iloc[0]
        if not str(root).endswith("\\"):
            root = str(root) + "\\"
        warnings.append(f"Raiz detectada: {root}")

    users_root = None
    if not roots.empty:
        root_str = str(roots.iloc[0])
        if not root_str.endswith("\\"):
            root_str += "\\"
        users_root = root_str + "Users\\"

    if users_root:
        user_dirs = paths[paths.str.match(re.escape(users_root) + r"[^\\]+$", na=False)]
        skip = {"Public", "Default", "Default User", "All Users"}
        user_dirs = user_dirs[~user_dirs.str.rstrip("\\").str.split("\\").str[-1].isin(skip)]
        if user_dirs.empty:
            warnings.append("Nenhum perfil de usuário detectado em Users\\.")
        else:
            warnings.append(f"Perfis em Users\\: {len(user_dirs)}")

    files_mask = (df[COL_FILES] == 0) & (df[COL_SUBDIRS] == 0)
    n_dirs = int((~files_mask).sum())
    n_files = int(files_mask.sum())
    total_gb = df[COL_PHYSICAL].sum() / 1_000_000_000
    warnings.append(
        f"{len(df):,} linhas — {n_dirs:,} pastas, {n_files:,} arquivos — ~{total_gb:.1f} GB físicos".replace(
            ",", "."
        )
    )

    try:
        pd.to_datetime(df[COL_MTIME], utc=True, errors="raise")
    except Exception:
        warnings.append(f"Coluna '{COL_MTIME}' contém datas inválidas — gráfico por ano pode falhar.")

    return errors, warnings


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
