"""Modelos de dados da auditoria."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

import pandas as pd

RiskLevel = Literal["seguro", "cuidado", "nao_tocar"]


@dataclass
class CandidateRule:
    path_regex: str
    risk: RiskLevel
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


class Candidate(TypedDict):
    path: str
    size: float
    risk: RiskLevel
    category: str
    action: str
    rationale: str


class TierTotals(TypedDict):
    seguro: float
    cuidado: float
    nao_tocar: float


class PathMetric(TypedDict):
    path: str
    gb: float
    files: int


class TopFile(TypedDict):
    path: str
    gb: float
    mtime: str


class YearBucket(TypedDict):
    year: str
    files: int
    gb: float


class ExtBucket(TypedDict):
    ext: str
    count: int
    gb: float


class PatternHit(TypedDict):
    pattern: str
    gb: float
    hits: int


class ReportData(TypedDict):
    root_gb: float
    root_files: int
    tier_totals: TierTotals
    level2: list[PathMetric]
    appdata_local: list[PathMetric]
    appdata_roaming: list[PathMetric]
    top_files: list[TopFile]
    pattern_summary: list[PatternHit]
    candidates: list[Candidate]
    years_data: list[YearBucket]
    ext_top: list[ExtBucket]
    compression_delta_gb: float
    row_count: int
