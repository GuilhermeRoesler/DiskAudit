# Disk Audit — Exemplos de Uso

## 1. Fluxo básico (WinDirStat → relatório)

1. Abra o WinDirStat e escaneie a unidade (ex.: `C:`)
2. Aguarde o scan completo
3. Exporte a lista: **File → Export → CSV** (UTF-8)
4. Salve como `disk.csv` na raiz do projeto
5. Valide e gere o relatório:

```bash
pip install -r requirements.txt
python scripts/validate_csv.py disk.csv
python disk_audit.py disk.csv
```

6. Abra `disk_report.html` no navegador

## 2. Caminhos customizados

```bash
# CSV e saída em locais diferentes
python disk_audit.py "D:\exports\windirstat_c_drive.csv" -o "D:\reports\auditoria_julho.html"

# Template em diretório alternativo (útil para testes)
python disk_audit.py disk.csv -t . -o test_report.html
```

## 3. Validar CSV antes da análise

O script `scripts/validate_csv.py` verifica colunas, tipos, encoding e dá um resumo do conteúdo:

```bash
python scripts/validate_csv.py
python scripts/validate_csv.py "C:\Users\Gui\Desktop\scan.csv"
```

**Saída esperada (sucesso):**

```
Validando disk.csv…
  ⚠ Raiz detectada: C:\
  ⚠ Perfis em Users\: 1
  ⚠ 125.432 linhas — 18.204 pastas, 107.228 arquivos — ~487.3 GB físicos
OK — CSV pronto para disk_audit.py
```

**Saída esperada (falha):**

```
Validando disk.csv…
FALHOU:
  ✗ Colunas ausentes: Tamanho Físico, Última Alteração
  ✗ Colunas encontradas: Name, Files, Subdirs, Size
```

Se as colunas estiverem em inglês, reexporte com WinDirStat em português ou ajuste os nomes em `disk_audit.py` (`COL_*`).

## 4. Adicionar candidato para limpeza

**Cenário:** detectar pasta `.nuget\packages` acima de 1 GB.

Em `disk_audit.py`, adicionar à lista `CANDIDATE_RULES`:

```python
CandidateRule(
    r"\\\.nuget\\packages$",
    "seguro",
    "Cache de pacotes",
    "dotnet nuget locals all --clear",
    "generic",
    1.0,
),
```

Rodar e verificar no relatório:

```bash
python disk_audit.py
# Abrir disk_report.html → seção "Plano de ação"
# Filtrar por "seguro" ou buscar "nuget"
```

## 5. Adicionar padrão ao gráfico

**Cenário:** destacar pastas `.pnpm-store` no gráfico de padrões.

```python
# Em PATTERNS:
(".pnpm-store", r"\\\.pnpm-store$"),
```

Regenerar o relatório — o padrão aparece em "Padrões detectados (dedup por pasta-pai)".

## 6. Rationale customizado

**Cenário:** explicar tamanho de pasta Steam com detalhe dos jogos maiores.

```python
def rationale_steam(row: pd.Series, ctx: dict) -> str:
    return (
        f"Steam ocupa {_gb(row[COL_PHYSICAL]):.1f} GB. "
        "Desinstale jogos não usados pelo cliente Steam — não delete a pasta manualmente."
    )

# Registrar:
RATIONALE_FNS["steam"] = rationale_steam

# Usar na regra existente de Steam, trocando rationale_fn:
CandidateRule(r"\\AppData\\Local\\Steam$", "cuidado", "Jogos", "Desinstalar jogos não usados", "steam", 2.0),
```

## 7. Estender o dashboard

**Cenário:** exibir contagem de candidatos por categoria.

1. Em `analyze()`, adicionar campo ao dict `data`:

```python
from collections import Counter
# ...
"category_counts": dict(Counter(c["category"] for c in candidates)),
```

2. No template, consumir via JS:

```javascript
// Após const DATA = ...
console.log(DATA.category_counts); // debug
// Ou renderizar nova seção/tabela
```

3. Regenerar e testar no navegador (F12 → erros de console).

## 8. Interpretar o relatório

| Seção | O que olhar |
|-------|-------------|
| KPIs | GB recuperáveis "Seguro" vs "Com cuidado" |
| Resumo executivo | Top oportunidades em linguagem natural |
| Plano de ação | Filtrar "Apenas seguros" primeiro |
| Top 40 arquivos | Arquivos individuais grandes (vhdx, isos, backups) |
| Idade por ano | Arquivos antigos vs pico no ano corrente (caches) |

**Ordem recomendada de limpeza:**
1. Candidatos **seguro** (Lixeira, Temp, caches npm/pip)
2. Candidatos **cuidado** que você confirma não usar (Docker prune, node_modules inativos)
3. Revisar **não tocar** manualmente (Documents, Pictures)

## 9. Troubleshooting

| Problema | Solução |
|----------|---------|
| `Erro: arquivo não encontrado` | Coloque `disk.csv` na raiz ou passe caminho absoluto |
| Gráficos vazios | CSV pode não ter AppData/perfil detectado — ver warnings do validate |
| Colunas erradas | WinDirStat exportou em outro idioma — verificar nomes |
| Relatório abre sem estilo | Requer internet (Chart.js via CDN) |
| Candidato não aparece | Aumentar sensibilidade reduzindo `min_gb` na regra |
