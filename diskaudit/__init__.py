"""Disk Audit — auditoria determinística a partir de CSV do WinDirStat."""

from __future__ import annotations

from diskaudit.analyze import analyze, load_csv
from diskaudit.cli import main
from diskaudit.constants import (
    BYTES_PER_GB,
    COL_FILES,
    COL_LOGICAL,
    COL_MTIME,
    COL_PATH,
    COL_PHYSICAL,
    COL_SUBDIRS,
)
from diskaudit.models import CandidateRule, Frames
from diskaudit.render import render_html
from diskaudit.rules import CANDIDATE_RULES, PATTERNS

__version__ = "1.0.1"

__all__ = [
    "BYTES_PER_GB",
    "CANDIDATE_RULES",
    "COL_FILES",
    "COL_LOGICAL",
    "COL_MTIME",
    "COL_PATH",
    "COL_PHYSICAL",
    "COL_SUBDIRS",
    "CandidateRule",
    "Frames",
    "PATTERNS",
    "analyze",
    "load_csv",
    "main",
    "render_html",
    "__version__",
]
