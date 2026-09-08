"""Detecção de candidatos a limpeza (regras + casos especiais)."""

from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath

import pandas as pd

from diskaudit.constants import COL_PHYSICAL
from diskaudit.models import Frames
from diskaudit.query import find_dirs, find_files
from diskaudit.rationales import RATIONALE_FNS, rationale_generic, rationale_node_modules
from diskaudit.rules import CANDIDATE_RULES
from diskaudit.util import gb


def make_candidate(
    row: pd.Series, risk: str, category: str, action: str, rationale_key: str, ctx: dict
) -> dict:
    fn = RATIONALE_FNS.get(rationale_key, rationale_generic)
    return {
        "path": row["path_norm"],
        "size": gb(row[COL_PHYSICAL]),
        "risk": risk,
        "category": category,
        "action": action,
        "rationale": fn(row, ctx),
    }


def find_special_candidates(frames: Frames, user: str | None, ctx: dict) -> list[dict]:
    found: list[dict] = []

    if user:
        dl = user + "Downloads\\"
        escaped = re.escape(dl.rstrip("\\"))
        subdirs = frames.dirs[frames.dirs["path_norm"].str.match(rf"^{escaped}\\[^\\]+$", na=False)]
        for _, row in subdirs.iterrows():
            prefix = row["path_norm"]
            zips = frames.files[
                frames.files["path_norm"].str.startswith(prefix, na=False)
                & frames.files["path_norm"].str.endswith(".zip", na=False)
            ]
            if len(zips) >= 3 and row["gb"] >= 2:
                found.append(
                    make_candidate(
                        row, "cuidado", "Downloads", "Mover/deletar zips se já extraídos", "downloads_zip", ctx
                    )
                )

    nm = find_dirs(frames, r"\\node_modules$", 0.05)
    if not nm.empty and nm["gb"].sum() >= 2:
        found.append(
            {
                "path": "Múltiplos\\…\\node_modules",
                "size": round(float(nm["gb"].sum()), 2),
                "risk": "seguro",
                "category": "Dev (node_modules)",
                "action": "npx npkill ou deletar node_modules de projetos inativos",
                "rationale": rationale_node_modules(nm.iloc[0], ctx),
            }
        )

    dist_rows = find_dirs(frames, r"\\dist$", 1.0).head(3)
    for _, row in dist_rows.iterrows():
        parent = PureWindowsPath(row["path_norm"]).parent
        # Checagem local opcional (no Windows real); no CSV sintético raramente casa.
        if Path(parent).joinpath("package.json").exists() or Path(parent).joinpath("src").exists():
            found.append(
                make_candidate(row, "seguro", "Dev (build artifact)", "Deletar dist/ — regenere com build", "dist", ctx)
            )

    for regex, cat, action in [
        (r"\\\.cache\\huggingface$", "Cache ML", "Deletar modelos HF não usados"),
        (r"\\\.ollama\\models$", "Modelos LLM", "Remover modelos Ollama não usados"),
    ]:
        for _, row in find_dirs(frames, regex, 1.0).iterrows():
            found.append(make_candidate(row, "cuidado", cat, action, "generic", ctx))

    return found


def find_candidates(frames: Frames, user: str | None) -> list[dict]:
    ctx = {"frames": frames}
    candidates: list[dict] = []
    seen_paths: set[str] = set()

    for rule in CANDIDATE_RULES:
        hits = find_dirs(frames, rule.path_regex, rule.min_gb)
        if hits.empty and rule.path_regex.endswith(r"\.sys$"):
            hits = find_files(frames, rule.path_regex, rule.min_gb)
        for _, row in hits.iterrows():
            path = rule.path_label or row["path_norm"]
            if path in seen_paths:
                continue
            if rule.risk == "nao_tocar" and user:
                if not row["path_norm"].startswith(user.rstrip("\\")):
                    continue
            fn = RATIONALE_FNS.get(rule.rationale_fn, rationale_generic)
            candidates.append(
                {
                    "path": path,
                    "size": gb(row[COL_PHYSICAL]),
                    "risk": rule.risk,
                    "category": rule.category,
                    "action": rule.action,
                    "rationale": fn(row, ctx),
                }
            )
            seen_paths.add(path)

    for special in find_special_candidates(frames, user, ctx):
        if special["path"] not in seen_paths:
            candidates.append(special)
            seen_paths.add(special["path"])

    candidates.sort(key=lambda c: c["size"], reverse=True)
    return candidates


def compute_tier_totals(candidates: list[dict]) -> dict[str, float]:
    totals = {"seguro": 0.0, "cuidado": 0.0, "nao_tocar": 0.0}
    for c in candidates:
        totals[c["risk"]] = round(totals.get(c["risk"], 0) + float(c["size"]), 1)
    return totals
