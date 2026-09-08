"""Utilitários de formatação e log."""

from __future__ import annotations

from pathlib import PureWindowsPath

from diskaudit.constants import BYTES_PER_GB


def log(msg: str) -> None:
    print(msg, flush=True)


def gb(bytes_val: int | float) -> float:
    return round(float(bytes_val) / BYTES_PER_GB, 2)


def fmt_files(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def win_path(path: str) -> PureWindowsPath:
    """Paths do WinDirStat são sempre estilo Windows, inclusive na CI Linux."""
    return PureWindowsPath(path)
