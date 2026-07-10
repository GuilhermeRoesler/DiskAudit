---
name: disk-audit
description: >-
  Gera relatórios HTML de auditoria de disco a partir de export CSV do WinDirStat.
  Use ao trabalhar neste repositório, ao modificar disk_audit.py, disk_dashboard_template.html,
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

| Arquivo | Papel |
|---------|-------|
| `disk_audit.py` | Script principal — leitura CSV, análise, renderização |
| `disk_dashboard_template.html` | Template Jinja2 + dashboard Chart.js (tema escuro) |
| `disk.csv` | Entrada padrão (export WinDirStat; gitignored) |
| `disk_report.html` | Saída gerada (gitignored) |
| `requirements.txt` | `pandas>=2.0`, `jinja2>=3.1` |

## Fluxo de execução

```bash
pip install -r requirements.txt
python disk_audit.py [disk.csv] [-o disk_report.html] [-t template_dir]
```

1. `load_csv()` — lê CSV UTF-8, normaliza paths (`/` → `\`), separa pastas vs arquivos
2. `analyze()` — detecta raiz, perfil de usuário, agrega métricas e candidatos
3. `render_html()` — injeta `data_json` no template via Jinja2

## Formato do CSV (WinDirStat)

Colunas esperadas (nomes exatos, em português):

| Coluna | Uso |
|--------|-----|
| `Nome` | Caminho completo |
| `Arquivos` | Contagem de arquivos na pasta |
| `Subdiretórios` | Contagem de subpastas |
| `Tamanho Físico` | Bytes em disco (métrica principal) |
| `Tamanho Lógico` | Bytes lógicos (para delta de compressão NTFS) |
| `Última Alteração` | Data de modificação |

**Convenções de processamento:**
- `BYTES_PER_GB = 1_000_000_000` (decimal, não GiB)
- Arquivo = `Arquivos == 0` e `Subdiretórios == 0`
- Paths normalizados em `path_norm` com barras invertidas

## Arquitetura de análise

```
CSV → Frames (all, dirs, files)
         ↓
    detect_root() + detect_user_profile()
         ↓
    compute_*() — level2, appdata, top_files, years, extensions, patterns
         ↓
    find_candidates() — CANDIDATE_RULES + find_special_candidates()
         ↓
    build_executive_summary() + render_html()
```

### Detecção automática

- **Raiz:** primeira linha que casa com `^[A-Z]:\$?`; fallback = menor profundidade de `\`
- **Perfil de usuário:** maior pasta em `{root}Users\{nome}\`, excluindo `Public`, `Default`, `Default User`, `All Users`

## Classificação de risco

Três níveis usados em candidatos e UI:

| Valor | Label UI | Significado |
|-------|----------|-------------|
| `seguro` | Seguro | Lixo/cache confirmado; ação reversível |
| `cuidado` | Cuidado | Depende do uso atual do usuário |
| `nao_tocar` | Não tocar | Dados pessoais ou sistema — revisar/backup |

Regras em `CANDIDATE_RULES` (`CandidateRule` dataclass): `path_regex`, `risk`, `category`, `action`, `rationale_fn`, `min_gb`.

Candidatos especiais (não cobertos por regras fixas) em `find_special_candidates()`:
- Subpastas de Downloads com ≥3 `.zip` e ≥2 GB
- Agregado de `node_modules` (≥2 GB total)
- Pastas `dist/` com `package.json` ou `src/` no pai
- Caches HuggingFace e modelos Ollama

## Justificativas (rationales)

Funções em `RATIONALE_FNS` geram texto explicativo por candidato. Ao adicionar regra nova:

1. Criar função `rationale_*` se precisar de contexto extra (acesso a `ctx["frames"]`)
2. Registrar em `RATIONALE_FNS`
3. Referenciar pelo nome em `CandidateRule.rationale_fn`

Use `rationale_generic` quando texto simples bastar.

## Padrões globais (`PATTERNS`)

Lista `(nome, regex)` para o gráfico "Padrões detectados". Usa deduplicação por pasta-pai (anchors) para não somar subpastas aninhadas.

## Payload JSON (`data_json`)

Objeto serializado injetado no template. Campos principais:

- `root_gb`, `root_files`, `row_count`, `compression_delta_gb`
- `tier_totals` — `{ seguro, cuidado, nao_tocar }` em GB
- `level2` — pastas de 1º nível sob a raiz
- `appdata_local`, `appdata_roaming` — filhos diretos do AppData do usuário
- `candidates` — lista ordenada por `size` desc
- `top_files`, `years_data`, `ext_top`, `pattern_summary`

Cada candidato: `{ path, size, risk, category, action, rationale }`.

## Template HTML

- Jinja2 renderiza metadados estáticos; dados dinâmicos via `const DATA = {{ data_json }}`
- Chart.js 4.4 (CDN) para gráficos de barras
- Tabelas interativas com filtro e sort no client-side (JS vanilla)
- `summary_html` é HTML pré-formatado (`| safe`) — usar tags `<strong>`, `<code>` com cuidado
- Manter consistência visual: variáveis CSS em `:root`, pills `.safe`/`.warn`/`.info`

## Convenções de código

- **Minimize escopo** — alterações focadas; não refatorar sem pedido
- **Regex de paths** — sempre com barras duplas escapadas (`\\AppData\\Local\\Temp$`)
- **Thresholds** — `min_gb` em regras evita ruído; respeitar ao adicionar candidatos
- **Formatação** — `_gb()` arredonda 2 casas; `_fmt_files()` usa separador de milhar `.`
- **Sem dependências extras** — manter stack em pandas + jinja2 apenas
- **Gitignore** — não commitar `*.csv` nem `disk_report.html` (dados pessoais)

## Tarefas comuns

### Adicionar novo candidato de limpeza

1. Identificar regex de path e categoria adequada
2. Definir `risk` e `action` recomendada
3. Adicionar `CandidateRule` em `CANDIDATE_RULES`
4. Criar/registrar `rationale_fn` se necessário
5. Rodar `python disk_audit.py` e validar no relatório

### Adicionar padrão ao gráfico de padrões

Adicionar tupla em `PATTERNS` com nome legível e regex que case com pastas relevantes.

### Alterar dashboard

Editar `disk_dashboard_template.html`. Se novos campos forem necessários, estender o dict retornado por `analyze()` e consumir em JS via `DATA.*`.

## O que NÃO fazer

- Não integrar LLM/IA — análise é 100% baseada em regras
- Não deletar arquivos automaticamente — apenas recomendar ações
- Não alterar `BYTES_PER_GB` sem atualizar labels do dashboard
- Não expor paths reais do usuário em commits (CSV e report são gitignored)

## Referência detalhada

Para lista completa de regras, padrões e funções de rationale, ver [reference.md](reference.md).
