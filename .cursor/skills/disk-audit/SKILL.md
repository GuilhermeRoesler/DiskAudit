---
name: disk-audit
description: >-
  Gera relatórios HTML de auditoria de disco a partir de export CSV do WinDirStat.
  Use ao trabalhar neste repositório, ao modificar o pacote diskaudit/, o template HTML,
  regras de candidatos, padrões de detecção, ou ao pedir para analisar/estender a auditoria de disco.
---

# Disk Audit — Especificação do Projeto

## Visão geral

Ferramenta **determinística** (sem IA) que lê um CSV exportado pelo [WinDirStat](https://windirstat.net/) e produz um dashboard HTML interativo com:

- KPIs de uso do disco e potencial de recuperação
- Gráficos de distribuição (pastas raiz, AppData, padrões conhecidos)
- Plano de ação com candidatos a remoção classificados por risco
- Top arquivos, idade por ano e extensões

**Idioma:** todo conteúdo voltado ao usuário final é em **português (pt-BR)**.

## Estrutura de arquivos

| Arquivo / pasta | Papel |
|-----------------|-------|
| `diskaudit/` | Pacote instalável (analyze, candidates, rules, rationales, render, cli) |
| `diskaudit/templates/disk_dashboard_template.html` | Template Jinja2 + Chart.js embutido |
| `diskaudit/static/` | Chart.js vendored (offline) |
| `disk_audit.py` | Shim de compatibilidade (`python disk_audit.py`) |
| `disk.csv` | Entrada padrão (gitignored) |
| `disk_report.html` | Saída gerada (gitignored) |
| `requirements.txt` | `pandas>=2.0`, `jinja2>=3.1` |
| `pyproject.toml` | Empacotamento, Ruff, mypy, coverage, entry point `disk-audit` |
| `scripts/validate_csv.py` | Valida CSV antes da análise |
| `examples/demo_report.html` | Relatório demo anonymizado |
| `docs/` | Exemplos, referência e imagens |
| `CHANGELOG.md` | Histórico de versões |
| `CONTRIBUTING.md` / `SECURITY.md` | Contribuição e segurança |

## Fluxo de execução

```bash
pip install -e .
python scripts/validate_csv.py disk.csv   # opcional, recomendado
python disk_audit.py [disk.csv] [-o disk_report.html] [-t template_dir]
# ou: disk-audit disk.csv
```

1. `load_csv()` — lê CSV UTF-8, normaliza paths (`/` → `\`), separa pastas vs arquivos
2. `analyze()` — detecta raiz, perfil de usuário, agrega métricas e candidatos
3. `render_html()` — injeta `data_json` no template via Jinja2

## Formato do CSV (WinDirStat)

Colunas esperadas (nomes exatos, em português): `Nome`, `Arquivos`, `Subdiretórios`, `Tamanho Físico`, `Tamanho Lógico`, `Última Alteração`.

**Convenções:** `BYTES_PER_GB = 1_000_000_000`; arquivo = `Arquivos == 0` e `Subdiretórios == 0`; paths em `path_norm` com `\`.

## Arquitetura

```
CSV → Frames → detect_root/user → compute_* → find_candidates → render_html
```

Regras em `diskaudit/rules.py` (`CANDIDATE_RULES`, `PATTERNS`). Rationales em `diskaudit/rationales.py`. Candidatos especiais em `diskaudit/candidates.py`.

## Classificação de risco

| Valor | Significado |
|-------|-------------|
| `seguro` | Lixo/cache confirmado |
| `cuidado` | Depende do uso |
| `nao_tocar` | Pessoal/sistema |

## Convenções

- Minimize escopo; regex de paths com `\\`; thresholds `min_gb`; stack só pandas + jinja2
- Não commitar `*.csv` / `disk_report.html`; não integrar IA; não deletar arquivos automaticamente

## Recursos

- [docs/examples.md](../../../docs/examples.md)
- [docs/reference.md](../../../docs/reference.md)
- Demo: https://guilhermeroesler.github.io/DiskAudit/
