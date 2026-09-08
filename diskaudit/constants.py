"""Constantes compartilhadas (colunas WinDirStat e unidades)."""

from __future__ import annotations

BYTES_PER_GB = 1_000_000_000

COL_PATH = "Nome"
COL_FILES = "Arquivos"
COL_SUBDIRS = "Subdiretórios"
COL_PHYSICAL = "Tamanho Físico"
COL_LOGICAL = "Tamanho Lógico"
COL_MTIME = "Última Alteração"

SKIP_USER_PROFILES = ("Public", "Default", "Default User", "All Users")
