"""Validação de CSV exportado pelo WinDirStat."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from diskaudit.constants import (
    COL_FILES,
    COL_LOGICAL,
    COL_MTIME,
    COL_PATH,
    COL_PHYSICAL,
    COL_SUBDIRS,
    SKIP_USER_PROFILES,
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
        skip = set(SKIP_USER_PROFILES)
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
