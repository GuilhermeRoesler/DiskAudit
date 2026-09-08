"""Leitura do CSV e agregações da auditoria."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from diskaudit.candidates import compute_tier_totals, find_candidates
from diskaudit.constants import (
    BYTES_PER_GB,
    COL_FILES,
    COL_LOGICAL,
    COL_MTIME,
    COL_PATH,
    COL_PHYSICAL,
    COL_SUBDIRS,
    SKIP_USER_PROFILES,
)
from diskaudit.models import Frames
from diskaudit.rules import PATTERNS
from diskaudit.util import gb, log


def load_csv(path: Path) -> Frames:
    log(f"Lendo {path}…")
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
    df["gb"] = df[COL_PHYSICAL] / BYTES_PER_GB
    df["path_norm"] = df[COL_PATH].str.replace("/", "\\", regex=False)
    df["is_file"] = (df[COL_FILES] == 0) & (df[COL_SUBDIRS] == 0)
    dirs = df[~df["is_file"]].copy()
    files = df[df["is_file"] & (df[COL_PHYSICAL] > 0)].copy()
    log(f"  {len(df):,} linhas ({len(dirs):,} pastas, {len(files):,} arquivos)")
    return Frames(all=df, dirs=dirs, files=files)


def detect_root(frames: Frames) -> tuple[str, pd.Series]:
    roots = frames.all[frames.all["path_norm"].str.match(r"^[A-Z]:\\?$", na=False)]
    if roots.empty:
        depth = frames.all["path_norm"].map(lambda p: str(p).count("\\"))
        root_row = frames.all.loc[depth.idxmin()]
        root = root_row["path_norm"].rstrip("\\") + "\\"
        return root, root_row
    root_row = roots.iloc[0]
    root = root_row["path_norm"]
    if not root.endswith("\\"):
        root += "\\"
    return root, root_row


def detect_user_profile(frames: Frames, root: str) -> str | None:
    users_root = root + "Users\\"
    pattern = re.escape(users_root) + r"[^\\]+$"
    users = frames.dirs[frames.dirs["path_norm"].str.match(pattern, na=False)]
    users = users[~users["path_norm"].str.endswith(SKIP_USER_PROFILES)]
    if users.empty:
        return None
    path = users.loc[users["gb"].idxmax(), "path_norm"]
    return path if path.endswith("\\") else path + "\\"


def compute_level2(frames: Frames, root: str) -> list[dict]:
    escaped = re.escape(root.rstrip("\\"))
    pattern = rf"^{escaped}\\[^\\]+$"
    rows = frames.all[frames.all["path_norm"].str.match(pattern, na=False)].sort_values(
        "gb", ascending=False
    )
    return [
        {"path": r["path_norm"], "gb": gb(r[COL_PHYSICAL]), "files": int(r[COL_FILES])}
        for _, r in rows.iterrows()
    ]


def compute_appdata_children(frames: Frames, base: str, label_fn) -> list[dict]:
    escaped = re.escape(base.rstrip("\\"))
    pattern = rf"^{escaped}\\[^\\]+$"
    rows = frames.dirs[frames.dirs["path_norm"].str.match(pattern, na=False)].sort_values(
        "gb", ascending=False
    )
    return [
        {
            "path": label_fn(r["path_norm"]),
            "gb": gb(r[COL_PHYSICAL]),
            "files": int(r[COL_FILES]),
        }
        for _, r in rows.iterrows()
        if r["gb"] >= 0.1
    ]


def compute_top_files(frames: Frames, n: int = 40) -> list[dict]:
    top = frames.files.nlargest(n, COL_PHYSICAL)
    return [
        {
            "path": r["path_norm"],
            "gb": gb(r[COL_PHYSICAL]),
            "mtime": pd.to_datetime(r[COL_MTIME], utc=True).strftime("%Y-%m-%d"),
        }
        for _, r in top.iterrows()
    ]


def compute_years(frames: Frames) -> list[dict]:
    files = frames.files.copy()
    files["year"] = pd.to_datetime(files[COL_MTIME], utc=True).dt.year.astype(str)
    grouped = (
        files.groupby("year").agg(files=(COL_PATH, "count"), gb=(COL_PHYSICAL, "sum")).sort_index()
    )
    return [{"year": y, "files": int(r["files"]), "gb": gb(r["gb"])} for y, r in grouped.iterrows()]


def compute_extensions(frames: Frames, n: int = 20) -> list[dict]:
    files = frames.files.copy()

    def ext_of(path: str) -> str:
        name = Path(path).name
        if "." not in name:
            return "(no-ext)"
        return name.rsplit(".", 1)[-1].lower()

    files["ext"] = files["path_norm"].map(ext_of)
    grouped = (
        files.groupby("ext")
        .agg(count=(COL_PATH, "count"), gb=(COL_PHYSICAL, "sum"))
        .sort_values("gb", ascending=False)
        .head(n)
    )
    return [{"ext": e, "count": int(r["count"]), "gb": gb(r["gb"])} for e, r in grouped.iterrows()]


def compute_patterns(frames: Frames) -> list[dict]:
    results: list[dict] = []
    dirs = frames.dirs
    for name, regex in PATTERNS:
        matched = dirs[dirs["path_norm"].str.contains(regex, regex=True, na=False)]
        if matched.empty:
            continue
        paths = matched["path_norm"].tolist()
        anchors: list[str] = []
        for p in sorted(paths, key=len):
            if not any(p.startswith(a + "\\") for a in anchors):
                anchors.append(p)
        anchor_rows = matched[matched["path_norm"].isin(anchors)]
        results.append(
            {"pattern": name, "gb": gb(anchor_rows[COL_PHYSICAL].sum()), "hits": len(anchors)}
        )
    results.sort(key=lambda x: x["gb"], reverse=True)
    return results


def analyze(frames: Frames) -> tuple[dict, str, str | None]:
    root, root_row = detect_root(frames)
    user = detect_user_profile(frames, root)

    level2 = compute_level2(frames, root)
    appdata_local: list[dict] = []
    appdata_roaming: list[dict] = []
    if user:
        appdata_local = compute_appdata_children(
            frames, user + "AppData\\Local\\", lambda p: p.replace(user + "AppData\\Local\\", "")
        )
        appdata_roaming = compute_appdata_children(
            frames,
            user + "AppData\\Roaming\\",
            lambda p: p.replace(user + "AppData\\Roaming\\", ""),
        )

    candidates = find_candidates(frames, user)

    data = {
        "root_gb": gb(root_row[COL_PHYSICAL]),
        "root_files": int(root_row[COL_FILES]),
        "tier_totals": compute_tier_totals(candidates),
        "level2": level2,
        "appdata_local": appdata_local,
        "appdata_roaming": appdata_roaming,
        "top_files": compute_top_files(frames),
        "pattern_summary": compute_patterns(frames),
        "candidates": candidates,
        "years_data": compute_years(frames),
        "ext_top": compute_extensions(frames),
        "compression_delta_gb": round(gb(root_row[COL_LOGICAL]) - gb(root_row[COL_PHYSICAL]), 1),
        "row_count": len(frames.all),
    }
    return data, root, user
