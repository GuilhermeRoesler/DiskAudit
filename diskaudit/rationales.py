"""Justificativas textuais por tipo de candidato."""

from __future__ import annotations

import pandas as pd

from diskaudit.constants import COL_FILES, COL_MTIME, COL_PHYSICAL
from diskaudit.models import Frames
from diskaudit.query import find_dirs, find_files
from diskaudit.util import fmt_files, gb, win_path


def rationale_recycle(row: pd.Series, ctx: dict) -> str:
    return (
        f"{fmt_files(int(row[COL_FILES]))} arquivos na Lixeira ({gb(row[COL_PHYSICAL]):.1f} GB). "
        "Arquivos já marcados para exclusão — esvazie a Lixeira para liberar espaço."
    )


def rationale_temp(row: pd.Series, ctx: dict) -> str:
    return f"{gb(row[COL_PHYSICAL]):.1f} GB de temporários. Software recria o que precisar ao deletar."


def rationale_browser_cache(row: pd.Series, ctx: dict) -> str:
    return (
        f"{gb(row[COL_PHYSICAL]):.1f} GB / {fmt_files(int(row[COL_FILES]))} arquivos de cache. "
        "Limpe cache nas configurações de privacidade (não marque senhas/favoritos)."
    )


def rationale_npm_cache(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    extras = []
    for pat, label in [(r"\\AppData\\Local\\pnpm$", "pnpm"), (r"\\AppData\\Local\\pip\\cache$", "pip")]:
        hits = find_dirs(frames, pat, 0.5)
        if not hits.empty:
            extras.append(f"{label} ({gb(hits.iloc[0][COL_PHYSICAL]):.1f} GB)")
    extra = f" Idem: {', '.join(extras)}." if extras else ""
    return f"Cache npm ({gb(row[COL_PHYSICAL]):.1f} GB). Só cache — refaz download quando precisa.{extra}"


def rationale_winsxs(row: pd.Series, ctx: dict) -> str:
    return (
        f"Component store do Windows ({gb(row[COL_PHYSICAL]):.1f} GB). "
        "Não delete manualmente. Use: DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase"
    )


def rationale_llm_models(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    gguf = frames.files[
        frames.files["path_norm"].str.endswith(".gguf", na=False)
        & frames.files["path_norm"].str.contains(r"\\\.lmstudio\\", regex=True, na=False)
    ].nlargest(5, COL_PHYSICAL)
    parts = [f"{win_path(r['path_norm']).stem[:35]} ({gb(r[COL_PHYSICAL]):.1f} GB)" for _, r in gguf.iterrows()]
    detail = ", ".join(parts) if parts else f"{gb(row[COL_PHYSICAL]):.1f} GB total"
    return f"Modelos LLM: {detail}. Remova os não usados — redownload é rápido."


def rationale_orphan_claude(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    uwp = find_dirs(frames, r"\\AppData\\Local\\Packages\\Claude_", 1)
    uwp_gb = gb(uwp.iloc[0][COL_PHYSICAL]) if not uwp.empty else 0
    vhdx = find_files(frames, r"Claude-3p.*rootfs\.vhdx", 0)
    vhdx_gb = sum(gb(r[COL_PHYSICAL]) for _, r in vhdx.iterrows())
    return (
        f"Instalação antiga ({gb(row[COL_PHYSICAL]):.1f} GB). UWP ativa ~{uwp_gb:.1f} GB. "
        f"Bundles duplicados ~{vhdx_gb:.1f} GB. Confirme que o app funciona e delete esta pasta."
    )


def rationale_downloads_zip(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    prefix = row["path_norm"]
    zips = frames.files[
        frames.files["path_norm"].str.startswith(prefix, na=False)
        & frames.files["path_norm"].str.endswith(".zip", na=False)
    ]
    n = len(zips)
    oldest = pd.to_datetime(zips[COL_MTIME], utc=True).min().strftime("%Y-%m") if n else "?"
    return (
        f"{n} .zip ({gb(row[COL_PHYSICAL]):.1f} GB) desde ~{oldest}. "
        "Se já extraiu, delete. Senão, mova para HD externo ou nuvem."
    )


def rationale_node_modules(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    nm = find_dirs(frames, r"\\node_modules$", 0.05)
    total_gb = nm["gb"].sum()
    top = nm.nlargest(6, "gb")
    projects = [
        f"{win_path(r['path_norm']).parent.name} ({gb(r[COL_PHYSICAL]):.1f} GB)" for _, r in top.iterrows()
    ]
    return (
        f"{len(nm)} pastas node_modules ({total_gb:.1f} GB). "
        f"Maiores: {', '.join(projects)}. npm install recria."
    )


def rationale_docker(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    vhdx = find_files(frames, r"docker_data\.vhdx", 0)
    vhdx_gb = gb(vhdx.iloc[0][COL_PHYSICAL]) if not vhdx.empty else 0
    return (
        f"Docker ({gb(row[COL_PHYSICAL]):.1f} GB). docker_data.vhdx = {vhdx_gb:.1f} GB. "
        "Considere docker system prune -a --volumes."
    )


def rationale_wsl(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    vhdx = frames.files[
        frames.files["path_norm"].str.endswith("ext4.vhdx", na=False)
        & frames.files["path_norm"].str.contains(r"\\wsl\\", regex=True, na=False)
    ]
    sizes = [gb(r[COL_PHYSICAL]) for _, r in vhdx.iterrows()]
    return (
        f"{len(sizes)} distro(s) WSL ({', '.join(f'{s:.1f} GB' for s in sizes)}). "
        "Use wsl --unregister para remover não usadas."
    )


def rationale_android(row: pd.Series, ctx: dict) -> str:
    return f"Android SDK ({gb(row[COL_PHYSICAL]):.1f} GB). Remova system-images/API levels não usados no SDK Manager."


def rationale_avd(row: pd.Series, ctx: dict) -> str:
    return f"Emuladores ({gb(row[COL_PHYSICAL]):.1f} GB). Delete AVDs não usados no Android Studio."


def rationale_minecraft(row: pd.Series, ctx: dict) -> str:
    return (
        f"{gb(row[COL_PHYSICAL]):.1f} GB / {fmt_files(int(row[COL_FILES]))} arquivos. "
        "Limpe mods/packs ou delete se não joga."
    )


def rationale_updater(row: pd.Series, ctx: dict) -> str:
    frames: Frames = ctx["frames"]
    stale = frames.files[
        frames.files["path_norm"].str.contains(r"(?:updates_v2|updater)", regex=True, na=False)
        & frames.files["path_norm"].str.contains(r"Setup\.exe$|\.exe$", regex=True, na=False)
        & (frames.files[COL_PHYSICAL] > 100_000_000)
    ]
    names = [win_path(r["path_norm"]).name for _, r in stale.head(5).iterrows()]
    total = sum(gb(r[COL_PHYSICAL]) for _, r in stale.iterrows())
    return f"Instaladores de updater (~{total:.1f} GB). Ex.: {', '.join(names[:3])}. Seguro deletar após update."


def rationale_dist(row: pd.Series, ctx: dict) -> str:
    parent = win_path(row["path_norm"]).parent
    return f"dist/ ({gb(row[COL_PHYSICAL]):.1f} GB) em {parent.name}. Saída de build — regenere com npm run build."


def rationale_generic(row: pd.Series, ctx: dict) -> str:
    return f"{gb(row[COL_PHYSICAL]):.1f} GB / {fmt_files(int(row[COL_FILES]))} arquivos nesta localização."


def rationale_personal(row: pd.Series, ctx: dict) -> str:
    return f"Conteúdo pessoal ({gb(row[COL_PHYSICAL]):.1f} GB). Revise antes de deletar; considere backup em nuvem."


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
