"""Renderização do dashboard HTML via Jinja2."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from diskaudit.util import log

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE_DIR = PACKAGE_DIR / "templates"


def build_executive_summary(data: dict, user: str | None) -> str:
    total = data["root_gb"]
    users_entry = next(
        (x for x in data["level2"] if x["path"].rstrip("\\").endswith("Users")), None
    )
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
    user_part = (
        f", dos quais <strong>{users_pct}%</strong> estão em <code>{user_label}</code>"
        if users_pct
        else ""
    )

    return (
        f"Seu disco tem <span id=\"sum-total\"></span> em uso{user_part}. "
        f"Principais oportunidades: {hl_text}. "
        f"Há ~<strong>{safe:.0f} GB recuperáveis com segurança</strong> e "
        f"~<strong>{careful:.0f} GB</strong> que dependem das suas escolhas."
    )


def render_html(
    data: dict, root: str, user: str | None, template_dir: Path, output: Path
) -> None:
    env = Environment(
        loader=FileSystemLoader(template_dir), autoescape=select_autoescape(["html"])
    )
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
