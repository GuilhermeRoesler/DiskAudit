#!/usr/bin/env python3
"""Auditoria de disco a partir de export CSV do WinDirStat — sem IA."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

BYTES_PER_GB = 1_000_000_000

COL_PATH = "Nome"
COL_FILES = "Arquivos"
COL_SUBDIRS = "Subdiretórios"
COL_PHYSICAL = "Tamanho Físico"
COL_LOGICAL = "Tamanho Lógico"
COL_MTIME = "Última Alteração"

PATTERNS: list[tuple[str, str]] = [
    ("WinSxS", r"\\WinSxS$"),
    ("Downloads", r"\\Downloads$"),
    ("AppData\\Local\\Packages", r"\\AppData\\Local\\Packages$"),
    ("$Recycle.Bin", r"\\?\$Recycle\.Bin$"),
    ("wsl", r"\\wsl$"),
    ("AppData\\Local\\Programs", r"\\AppData\\Local\\Programs$"),
    ("Docker", r"\\Docker$"),
    ("node_modules", r"\\node_modules$"),
    ("AppData\\Local\\Temp", r"\\AppData\\Local\\Temp$"),
    ("Temp", r"\\Temp$"),
    ("Steam", r"\\Steam$"),
    (".cache", r"\\\.cache$"),
    (".vscode", r"\\\.vscode$"),
    ("AppData\\Roaming\\Code", r"\\AppData\\Roaming\\Code$"),
    (".gradle", r"\\\.gradle$"),
    ("Epic Games", r"\\Epic Games$"),
    ("Installer", r"\\Installer$"),
    ("AppData\\Local\\npm-cache", r"\\AppData\\Local\\npm-cache$"),
    ("Logs", r"\\Logs$"),
    ("AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cache", r"\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cache$"),
    ("AppData\\Local\\Mozilla\\Firefox\\Profiles\\…\\cache2", r"\\AppData\\Local\\Mozilla\\Firefox\\Profiles\\[^\\]+\\cache2$"),
    ("AppData\\Local\\Opera Software\\…\\Cache", r"\\AppData\\Local\\Opera Software\\[^\\]+\\Cache$"),
    ("AppData\\Local\\Google\\Chrome\\User Data", r"\\AppData\\Local\\Google\\Chrome\\User Data$"),
    ("AppData\\Local\\Discord", r"\\AppData\\Local\\Discord$"),
    (".m2", r"\\\.m2$"),
    ("OneDrive", r"\\OneDrive$"),
    ("AppData\\Local\\Microsoft\\Windows\\WebCache", r"\\AppData\\Local\\Microsoft\\Windows\\WebCache$"),
]

SKIP_USER_PROFILES = ("Public", "Default", "Default User", "All Users")


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


def log(msg: str) -> None:
    print(msg, flush=True)


def _gb(bytes_val: int | float) -> float:
    return round(float(bytes_val) / BYTES_PER_GB, 2)


def _fmt_files(n: int) -> str:
    return f"{n:,}".replace(",", ".")


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
        depth = frames.all["path_norm"].str.count("\\")
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
    rows = frames.all[frames.all["path_norm"].str.match(pattern, na=False)].sort_values("gb", ascending=False)
    return [{"path": r["path_norm"], "gb": _gb(r[COL_PHYSICAL]), "files": int(r[COL_FILES])} for _, r in rows.iterrows()]


def compute_appdata_children(frames: Frames, base: str, label_fn) -> list[dict]:
    escaped = re.escape(base.rstrip("\\"))
    pattern = rf"^{escaped}\\[^\\]+$"
    rows = frames.dirs[frames.dirs["path_norm"].str.match(pattern, na=False)].sort_values("gb", ascending=False)
    return [
        {"path": label_fn(r["path_norm"]), "gb": _gb(r[COL_PHYSICAL]), "files": int(r[COL_FILES])}
        for _, r in rows.iterrows()
        if r["gb"] >= 0.1
    ]


def compute_top_files(frames: Frames, n: int = 40) -> list[dict]:
    top = frames.files.nlargest(n, COL_PHYSICAL)
    return [
        {
            "path": r["path_norm"],
            "gb": _gb(r[COL_PHYSICAL]),
            "mtime": pd.to_datetime(r[COL_MTIME], utc=True).strftime("%Y-%m-%d"),
        }
        for _, r in top.iterrows()
    ]


def compute_years(frames: Frames) -> list[dict]:
    files = frames.files.copy()
    files["year"] = pd.to_datetime(files[COL_MTIME], utc=True).dt.year.astype(str)
    grouped = files.groupby("year").agg(files=(COL_PATH, "count"), gb=(COL_PHYSICAL, "sum")).sort_index()
    return [{"year": y, "files": int(r["files"]), "gb": _gb(r["gb"])} for y, r in grouped.iterrows()]


def compute_extensions(frames: Frames, n: int = 20) -> list[dict]:
    files = frames.files.copy()

    def ext_of(path: str) -> str:
        name = Path(path).name
        if "." not in name:
            return "(no-ext)"
        return name.rsplit(".", 1)[-1].lower()

    files["ext"] = files["path_norm"].map(ext_of)
    grouped = files.groupby("ext").agg(count=(COL_PATH, "count"), gb=(COL_PHYSICAL, "sum")).sort_values("gb", ascending=False).head(n)
    return [{"ext": e, "count": int(r["count"]), "gb": _gb(r["gb"])} for e, r in grouped.iterrows()]


def compute_patterns(frames: Frames) -> list[dict]:
    results = []
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
        results.append({"pattern": name, "gb": _gb(anchor_rows[COL_PHYSICAL].sum()), "hits": len(anchors)})
    results.sort(key=lambda x: x["gb"], reverse=True)
    return results


def _find_dirs(frames: Frames, regex: str, min_gb: float = 0) -> pd.DataFrame:
    mask = frames.dirs["path_norm"].str.contains(regex, regex=True, na=False) & (frames.dirs["gb"] >= min_gb)
    return frames.dirs[mask]


def _find_files(frames: Frames, regex: str, min_gb: float = 0) -> pd.DataFrame:
    mask = frames.files["path_norm"].str.contains(regex, regex=True, na=False) & (frames.files["gb"] >= min_gb)
    return frames.files[mask]


# --- Rationale builders ---

def rationale_recycle(row: pd.Series, ctx: dict) -> str:
    return (
        f"{_fmt_files(int(row[COL_FILES]))} arquivos na Lixeira ({_gb(row[COL_PHYSICAL]):.1f} GB). "
        "Arquivos já marcados para exclusão — esvazie a Lixeira para liberar espaço."
    )


def rationale_temp(row: pd.Series, ctx: dict) -> str:
    return f"{_gb(row[COL_PHYSICAL]):.1f} GB de temporários. Software recria o que precisar ao deletar."


def rationale_browser_cache(row: pd.Series, ctx: dict) -> str:
    return (
        f"{_gb(row[COL_PHYSICAL]):.1f} GB / {_fmt_files(int(row[COL_FILES]))} arquivos de cache. "
        "Limpe cache nas configurações de privacidade (não marque senhas/favoritos)."
    )


def rationale_npm_cache(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    extras = []
    for pat, label in [(r"\\AppData\\Local\\pnpm$", "pnpm"), (r"\\AppData\\Local\\pip\\cache$", "pip")]:
        hits = _find_dirs(frames, pat, 0.5)
        if not hits.empty:
            extras.append(f"{label} ({_gb(hits.iloc[0][COL_PHYSICAL]):.1f} GB)")
    extra = f" Idem: {', '.join(extras)}." if extras else ""
    return f"Cache npm ({_gb(row[COL_PHYSICAL]):.1f} GB). Só cache — refaz download quando precisa.{extra}"


def rationale_winsxs(row: pd.Series, ctx: dict) -> str:
    return (
        f"Component store do Windows ({_gb(row[COL_PHYSICAL]):.1f} GB). "
        "Não delete manualmente. Use: DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase"
    )


def rationale_llm_models(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    gguf = frames.files[
        frames.files["path_norm"].str.endswith(".gguf", na=False)
        & frames.files["path_norm"].str.contains(r"\\\.lmstudio\\", regex=True, na=False)
    ].nlargest(5, COL_PHYSICAL)
    parts = [f"{Path(r['path_norm']).stem[:35]} ({_gb(r[COL_PHYSICAL]):.1f} GB)" for _, r in gguf.iterrows()]
    detail = ", ".join(parts) if parts else f"{_gb(row[COL_PHYSICAL]):.1f} GB total"
    return f"Modelos LLM: {detail}. Remova os não usados — redownload é rápido."


def rationale_orphan_claude(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    uwp = _find_dirs(frames, r"\\AppData\\Local\\Packages\\Claude_", 1)
    uwp_gb = _gb(uwp.iloc[0][COL_PHYSICAL]) if not uwp.empty else 0
    vhdx = _find_files(frames, r"Claude-3p.*rootfs\.vhdx", 0)
    vhdx_gb = sum(_gb(r[COL_PHYSICAL]) for _, r in vhdx.iterrows())
    return (
        f"Instalação antiga ({_gb(row[COL_PHYSICAL]):.1f} GB). UWP ativa ~{uwp_gb:.1f} GB. "
        f"Bundles duplicados ~{vhdx_gb:.1f} GB. Confirme que o app funciona e delete esta pasta."
    )


def rationale_downloads_zip(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    prefix = row["path_norm"]
    zips = frames.files[frames.files["path_norm"].str.startswith(prefix, na=False) & frames.files["path_norm"].str.endswith(".zip", na=False)]
    n = len(zips)
    oldest = pd.to_datetime(zips[COL_MTIME], utc=True).min().strftime("%Y-%m") if n else "?"
    return (
        f"{n} .zip ({_gb(row[COL_PHYSICAL]):.1f} GB) desde ~{oldest}. "
        "Se já extraiu, delete. Senão, mova para HD externo ou nuvem."
    )


def rationale_node_modules(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    nm = _find_dirs(frames, r"\\node_modules$", 0.05)
    total_gb = nm["gb"].sum()
    top = nm.nlargest(6, "gb")
    projects = [f"{Path(r['path_norm']).parent.name} ({_gb(r[COL_PHYSICAL]):.1f} GB)" for _, r in top.iterrows()]
    return f"{len(nm)} pastas node_modules ({total_gb:.1f} GB). Maiores: {', '.join(projects)}. npm install recria."


def rationale_docker(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    vhdx = _find_files(frames, r"docker_data\.vhdx", 0)
    vhdx_gb = _gb(vhdx.iloc[0][COL_PHYSICAL]) if not vhdx.empty else 0
    return f"Docker ({_gb(row[COL_PHYSICAL]):.1f} GB). docker_data.vhdx = {vhdx_gb:.1f} GB. Considere docker system prune -a --volumes."


def rationale_wsl(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    vhdx = frames.files[frames.files["path_norm"].str.endswith("ext4.vhdx", na=False) & frames.files["path_norm"].str.contains(r"\\wsl\\", regex=True, na=False)]
    sizes = [_gb(r[COL_PHYSICAL]) for _, r in vhdx.iterrows()]
    return f"{len(sizes)} distro(s) WSL ({', '.join(f'{s:.1f} GB' for s in sizes)}). Use wsl --unregister para remover não usadas."


def rationale_android(row: pd.Series, ctx: dict) -> str:
    return f"Android SDK ({_gb(row[COL_PHYSICAL]):.1f} GB). Remova system-images/API levels não usados no SDK Manager."


def rationale_avd(row: pd.Series, ctx: dict) -> str:
    return f"Emuladores ({_gb(row[COL_PHYSICAL]):.1f} GB). Delete AVDs não usados no Android Studio."


def rationale_minecraft(row: pd.Series, ctx: dict) -> str:
    return f"{_gb(row[COL_PHYSICAL]):.1f} GB / {_fmt_files(int(row[COL_FILES]))} arquivos. Limpe mods/packs ou delete se não joga."


def rationale_updater(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    stale = frames.files[
        frames.files["path_norm"].str.contains(r"(?:updates_v2|updater)", regex=True, na=False)
        & frames.files["path_norm"].str.contains(r"Setup\.exe$|\.exe$", regex=True, na=False)
        & (frames.files[COL_PHYSICAL] > 100_000_000)
    ]
    names = [Path(r["path_norm"]).name for _, r in stale.head(5).iterrows()]
    total = sum(_gb(r[COL_PHYSICAL]) for _, r in stale.iterrows())
    return f"Instaladores de updater (~{total:.1f} GB). Ex.: {', '.join(names[:3])}. Seguro deletar após update."


def rationale_dist(row: pd.Series, ctx: dict) -> str:
    parent = Path(row["path_norm"]).parent
    return f"dist/ ({_gb(row[COL_PHYSICAL]):.1f} GB) em {parent.name}. Saída de build — regenere com npm run build."


def rationale_generic(row: pd.Series, ctx: dict) -> str:
    return f"{_gb(row[COL_PHYSICAL]):.1f} GB / {_fmt_files(int(row[COL_FILES]))} arquivos nesta localização."


def rationale_personal(row: pd.Series, ctx: dict) -> str:
    return f"Conteúdo pessoal ({_gb(row[COL_PHYSICAL]):.1f} GB). Revise antes de deletar; considere backup em nuvem."


def rationale_system(row: pd.Series, ctx: dict) -> str:
    return "Arquivo de sistema gerenciado pelo Windows. Não altere manualmente."


RATIONALE_FNS = {
    "recycle": rationale_recycle,
    "temp": rationale_temp,
    "browser_cache": rationale_browser_cache,
    "npm_cache": rationale_npm_cache,
    "winsxs": rationale_winsxs,
    "llm_models": rationale_llm_models,
    "orphan_claude": rationale_orphan_claude,
    "downloads_zip": rationale_downloads_zip,
    "node_modules": rationale_node_modules,
    "docker": rationale_docker,
    "wsl": rationale_wsl,
    "android": rationale_android,
    "avd": rationale_avd,
    "minecraft": rationale_minecraft,
    "updater": rationale_updater,
    "dist": rationale_dist,
    "generic": rationale_generic,
    "personal": rationale_personal,
    "system": rationale_system,
}


CANDIDATE_RULES: list[CandidateRule] = [
    CandidateRule(r"\\?\$Recycle\.Bin$", "seguro", "Lixeira", "Esvaziar Lixeira", "recycle", 0.1),
    CandidateRule(r"\\AppData\\Local\\Temp$", "seguro", "Cache", "Esvaziar %temp%", "temp", 0.5),
    CandidateRule(r"\\AppData\\Local\\Opera Software\\[^\\]+\\Cache$", "seguro", "Cache de navegador", "Limpar cache do Opera", "browser_cache", 0.3),
    CandidateRule(r"\\AppData\\Local\\Mozilla\\Firefox\\Profiles\\[^\\]+\\cache2$", "seguro", "Cache de navegador", "Limpar cache do Firefox", "browser_cache", 0.3),
    CandidateRule(r"\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cache$", "seguro", "Cache de navegador", "Limpar cache do Chrome", "browser_cache", 0.3),
    CandidateRule(r"\\AppData\\Local\\npm-cache$", "seguro", "Cache de pacotes", "npm cache clean --force", "npm_cache", 0.5),
    CandidateRule(r"\\AppData\\Local\\pnpm$", "seguro", "Cache de pacotes", "pnpm store prune", "npm_cache", 0.5),
    CandidateRule(r"\\AppData\\Local\\pip\\cache$", "seguro", "Cache de pacotes", "pip cache purge", "npm_cache", 0.5),
    CandidateRule(r"\\Windows\\WinSxS$", "cuidado", "Windows", "DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase", "winsxs", 5.0),
    CandidateRule(r"\\\.lmstudio\\models$", "cuidado", "Modelos LLM", "Manter apenas modelos em uso", "llm_models", 5.0),
    CandidateRule(r"\\AppData\\Local\\Claude-3p$", "cuidado", "App órfão", "Deletar após confirmar versão UWP do Claude", "orphan_claude", 1.0),
    CandidateRule(r"\\AppData\\Local\\Docker$", "cuidado", "Dev (Docker)", "docker system prune -a --volumes", "docker", 2.0),
    CandidateRule(r"\\AppData\\Local\\wsl$", "cuidado", "Dev (WSL)", "wsl --unregister distros não usadas", "wsl", 1.0),
    CandidateRule(r"\\AppData\\Local\\Android$", "cuidado", "Dev (Android)", "SDK Manager → remover APIs não usadas", "android", 2.0),
    CandidateRule(r"\\\.android\\avd$", "cuidado", "Dev (Android)", "Remover emuladores não usados", "avd", 2.0),
    CandidateRule(r"\\AppData\\Roaming\\\.minecraft$", "cuidado", "Jogo", "Limpar mods/packs ou desinstalar", "minecraft", 3.0),
    CandidateRule(r"\\AppData\\Local\\Roblox$", "cuidado", "Jogo", "Desinstalar se não joga", "generic", 2.0),
    CandidateRule(r"\\AppData\\Local\\CapCut$", "cuidado", "Edição de vídeo", "Limpar cache de mídia no CapCut", "generic", 1.0),
    CandidateRule(r"\\AppData\\Local\\Steam$", "cuidado", "Jogos", "Desinstalar jogos não usados", "generic", 2.0),
    CandidateRule(r"\\AppData\\Local\\EpicGames$", "cuidado", "Jogos", "Desinstalar jogos Epic não usados", "generic", 2.0),
    CandidateRule(r"\\AppData\\Local\\BlueStacks", "cuidado", "Emulador", "Desinstalar se não usa", "generic", 0.5),
    CandidateRule(r"\\AppData\\Local\\Ollama$", "seguro", "Cache de updater", "Deletar updates_v2/", "updater", 0.5),
    CandidateRule(r"\\Music$", "nao_tocar", "Pessoal (música)", "Backup em nuvem/HD externo", "personal", 3.0),
    CandidateRule(r"\\Videos$", "nao_tocar", "Pessoal (vídeo)", "Mover para nuvem se pouco acessado", "personal", 3.0),
    CandidateRule(r"\\Pictures$", "nao_tocar", "Pessoal", "Revisar manualmente", "personal", 2.0),
    CandidateRule(r"\\Documents$", "nao_tocar", "Pessoal (documentos)", "Revisar manualmente", "personal", 5.0),
    CandidateRule(r"\\pagefile\.sys$", "nao_tocar", "Sistema", "Não mexer (Windows gerencia)", "system", 0.1),
    CandidateRule(r"\\hiberfil\.sys$", "nao_tocar", "Sistema", "Não mexer", "system", 0.1),
]


def _make_candidate(row: pd.Series, risk: str, category: str, action: str, rationale_key: str, ctx: dict) -> dict:
    fn = RATIONALE_FNS.get(rationale_key, rationale_generic)
    return {
        "path": row["path_norm"],
        "size": _gb(row[COL_PHYSICAL]),
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
            zips = frames.files[frames.files["path_norm"].str.startswith(prefix, na=False) & frames.files["path_norm"].str.endswith(".zip", na=False)]
            if len(zips) >= 3 and row["gb"] >= 2:
                found.append(_make_candidate(row, "cuidado", "Downloads", "Mover/deletar zips se já extraídos", "downloads_zip", ctx))

    nm = _find_dirs(frames, r"\\node_modules$", 0.05)
    if not nm.empty and nm["gb"].sum() >= 2:
        found.append(
            {
                "path": "Múltiplos\\…\\node_modules",
                "size": round(nm["gb"].sum(), 2),
                "risk": "seguro",
                "category": "Dev (node_modules)",
                "action": "npx npkill ou deletar node_modules de projetos inativos",
                "rationale": rationale_node_modules(nm.iloc[0], ctx),
            }
        )

    dist_rows = _find_dirs(frames, r"\\dist$", 1.0).head(3)
    for _, row in dist_rows.iterrows():
        parent = Path(row["path_norm"]).parent
        if (parent / "package.json").exists() or parent.joinpath("src").exists():
            found.append(_make_candidate(row, "seguro", "Dev (build artifact)", "Deletar dist/ — regenere com build", "dist", ctx))

    for regex, cat, action in [
        (r"\\\.cache\\huggingface$", "Cache ML", "Deletar modelos HF não usados"),
        (r"\\\.ollama\\models$", "Modelos LLM", "Remover modelos Ollama não usados"),
    ]:
        for _, row in _find_dirs(frames, regex, 1.0).iterrows():
            found.append(_make_candidate(row, "cuidado", cat, action, "generic", ctx))

    return found


def find_candidates(frames: Frames, user: str | None) -> list[dict]:
    ctx = {"frames": frames}
    candidates: list[dict] = []
    seen_paths: set[str] = set()

    for rule in CANDIDATE_RULES:
        hits = _find_dirs(frames, rule.path_regex, rule.min_gb)
        if hits.empty and rule.path_regex.endswith(r"\.sys$"):
            hits = _find_files(frames, rule.path_regex, rule.min_gb)
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
                    "size": _gb(row[COL_PHYSICAL]),
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
        totals[c["risk"]] = round(totals.get(c["risk"], 0) + c["size"], 1)
    return totals


def build_executive_summary(data: dict, user: str | None) -> str:
    total = data["root_gb"]
    users_entry = next((x for x in data["level2"] if x["path"].rstrip("\\").endswith("Users")), None)
    users_pct = round(users_entry["gb"] / total * 100) if users_entry and total else 0
    user_label = user.rstrip("\\") if user else "Users\\…"

    safe = data["tier_totals"]["seguro"]
    careful = data["tier_totals"]["cuidado"]

    highlights = []
    for c in data["candidates"]:
        if c["risk"] == "nao_tocar":
            continue
        name = c["path"].split("\\")[-1][:40] or c["path"][:40]
        highlights.append(f"<strong>{name}</strong> ({c['size']:.1f} GB — {c['category'].lower()})")
        if len(highlights) >= 4:
            break

    hl_text = "; ".join(highlights) if highlights else "nenhum candidato destacado"
    user_part = f", dos quais <strong>{users_pct}%</strong> estão em <code>{user_label}</code>" if users_pct else ""

    return (
        f"Seu disco tem <span id=\"sum-total\"></span> em uso{user_part}. "
        f"Principais oportunidades: {hl_text}. "
        f"Há ~<strong>{safe:.0f} GB recuperáveis com segurança</strong> e "
        f"~<strong>{careful:.0f} GB</strong> que dependem das suas escolhas."
    )


def analyze(frames: Frames) -> tuple[dict, str, str | None]:
    root, root_row = detect_root(frames)
    user = detect_user_profile(frames, root)

    level2 = compute_level2(frames, root)
    appdata_local: list[dict] = []
    appdata_roaming: list[dict] = []
    if user:
        appdata_local = compute_appdata_children(frames, user + "AppData\\Local\\", lambda p: p.replace(user + "AppData\\Local\\", ""))
        appdata_roaming = compute_appdata_children(frames, user + "AppData\\Roaming\\", lambda p: p.replace(user + "AppData\\Roaming\\", ""))

    candidates = find_candidates(frames, user)

    data = {
        "root_gb": _gb(root_row[COL_PHYSICAL]),
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
        "compression_delta_gb": round(_gb(root_row[COL_LOGICAL]) - _gb(root_row[COL_PHYSICAL]), 1),
        "row_count": len(frames.all),
    }
    return data, root, user


def render_html(data: dict, root: str, user: str | None, template_dir: Path, output: Path) -> None:
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(["html"]))
    html = env.get_template("disk_dashboard_template.html").render(
        drive_label=root.rstrip("\\"),
        title_gb=int(data["root_gb"]),
        processed_date=datetime.now().strftime("%d/%m/%Y"),
        summary_html=build_executive_summary(data, user),
        data_json=json.dumps(data, ensure_ascii=False),
        row_count=f"{data['row_count']:,}".replace(",", "."),
        compression_delta=data.get("compression_delta_gb", 0),
    )
    output.write_text(html, encoding="utf-8")
    log(f"Relatório salvo em {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoria de disco a partir de CSV do WinDirStat")
    parser.add_argument("csv", nargs="?", default="disk.csv", help="Caminho do CSV exportado")
    parser.add_argument("-o", "--output", default="disk_report.html", help="Arquivo HTML de saída")
    parser.add_argument("-t", "--template-dir", default=None, help="Diretório do template")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = script_dir / csv_path
    if not csv_path.exists():
        log(f"Erro: arquivo não encontrado: {csv_path}")
        return 1

    template_dir = Path(args.template_dir) if args.template_dir else script_dir
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = script_dir / output_path

    frames = load_csv(csv_path)
    log("Analisando…")
    data, root, user = analyze(frames)
    log(f"  Raiz: {root} | Perfil: {user or 'não detectado'}")
    log(f"  {data['root_gb']:.1f} GB | {len(data['candidates'])} candidatos")

    render_html(data, root, user, template_dir, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
