#!/usr/bin/env python3
"""Compatibilidade: `python disk_audit.py` e imports legados `import disk_audit`."""

from __future__ import annotations

import sys

from diskaudit import (  # noqa: F401
    BYTES_PER_GB,
    CANDIDATE_RULES,
    COL_FILES,
    COL_LOGICAL,
    COL_MTIME,
    COL_PATH,
    COL_PHYSICAL,
    COL_SUBDIRS,
    PATTERNS,
    CandidateRule,
    Frames,
    __version__,
    analyze,
    load_csv,
    main,
    render_html,
)
from diskaudit.analyze import (  # noqa: F401
    compute_extensions,
    compute_level2,
    compute_patterns,
    compute_top_files,
    compute_years,
    detect_root,
    detect_user_profile,
)
from diskaudit.candidates import (  # noqa: F401
    compute_tier_totals,
    find_candidates,
    find_special_candidates,
)
from diskaudit.rationales import RATIONALE_FNS  # noqa: F401
from diskaudit.render import build_executive_summary  # noqa: F401
from diskaudit.util import fmt_files as _fmt_files  # noqa: F401
from diskaudit.util import gb as _gb  # noqa: F401
from diskaudit.util import log  # noqa: F401

if __name__ == "__main__":
    sys.exit(main())
