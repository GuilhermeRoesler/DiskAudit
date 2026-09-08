"""Consultas sobre Frames (pastas/arquivos por regex)."""

from __future__ import annotations

import pandas as pd

from diskaudit.models import Frames


def find_dirs(frames: Frames, regex: str, min_gb: float = 0) -> pd.DataFrame:
    mask = frames.dirs["path_norm"].str.contains(regex, regex=True, na=False) & (
        frames.dirs["gb"] >= min_gb
    )
    return frames.dirs[mask]


def find_files(frames: Frames, regex: str, min_gb: float = 0) -> pd.DataFrame:
    mask = frames.files["path_norm"].str.contains(regex, regex=True, na=False) & (
        frames.files["gb"] >= min_gb
    )
    return frames.files[mask]
