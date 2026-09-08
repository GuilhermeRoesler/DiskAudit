"""Modelos de dados da auditoria."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class CandidateRule:
    path_regex: str
    risk: str
    category: str
    action: str
    rationale_fn: str
    min_gb: float = 0.5
    path_label: str | None = None


@dataclass
class Frames:
    all: pd.DataFrame
    dirs: pd.DataFrame
    files: pd.DataFrame
