# Disk Audit

Auditoria de disco **determinística** (sem IA) a partir de export CSV do [WinDirStat](https://windirstat.net/). Gera um dashboard HTML interativo com KPIs, gráficos e um plano de ação classificado por risco — tudo em português.

## O que faz

- Lê um snapshot do WinDirStat e detecta automaticamente a unidade e o perfil de usuário
- Identifica candidatos a limpeza (Lixeira, Temp, caches, Docker, WSL, jogos, etc.)
- Classifica cada item em **Seguro**, **Cuidado** ou **Não tocar**
- Exibe distribuição por pastas raiz, AppData e padrões conhecidos
- Lista os 40 maiores arquivos, idade por ano e top extensões

> **Atenção:** a ferramenta apenas **recomenda** ações. Nenhum arquivo é deletado automaticamente.

## Requisitos

- Python 3.10+
- [WinDirStat](https://windirstat.net/) para escanear o disco e exportar CSV
- Navegador moderno (o relatório usa Chart.js via CDN)

## Início rápido (Windows)

1. Escaneie a unidade no WinDirStat
2. Exporte: **File → Export → CSV** (UTF-8)
3. Salve como `disk.csv` na raiz deste projeto
4. Execute:

```bat
run.bat
```

O script instala dependências, gera `disk_report.html` e abre no navegador.

### Linha de comando

```bash
pip install -r requirements.txt
python scripts/validate_csv.py disk.csv   # opcional, recomendado
python disk_audit.py disk.csv
```

Abra `disk_report.html` manualmente se não usar `run.bat`.

## Uso avançado

```bash
# CSV e saída em caminhos customizados
python disk_audit.py "D:\exports\scan.csv" -o "D:\reports\auditoria.html"

# Diretório alternativo do template
python disk_audit.py disk.csv -t . -o test_report.html
```

| Argumento | Padrão | Descrição |
|-----------|--------|-----------|
| `csv` | `disk.csv` | Caminho do CSV exportado |
| `-o`, `--output` | `disk_report.html` | Arquivo HTML de saída |
| `-t`, `--template-dir` | diretório do script | Pasta com `disk_dashboard_template.html` |

## Formato do CSV

O export deve conter estas colunas (nomes em português, como no WinDirStat pt-BR):

| Coluna | Descrição |
|--------|-----------|
| `Nome` | Caminho completo |
| `Arquivos` | Contagem de arquivos |
| `Subdiretórios` | Contagem de subpastas |
| `Tamanho Físico` | Bytes em disco (métrica principal) |
| `Tamanho Lógico` | Bytes lógicos |
| `Última Alteração` | Data de modificação |

Colunas extras (ex.: `Atributos`) são ignoradas.

## Validar CSV

Antes de gerar o relatório, use o validador para checar colunas, encoding e conteúdo:

```bash
python scripts/validate_csv.py disk.csv
```

Retorna exit code `0` se OK, `1` se inválido.

## Relatório gerado

O dashboard inclui:

| Seção | Conteúdo |
|-------|----------|
| KPIs | Total em uso, arquivos, % em Users, GB recuperáveis |
| Resumo executivo | Principais oportunidades em linguagem natural |
| Gráficos | Pastas raiz, AppData Local/Roaming, padrões detectados |
| Plano de ação | Candidatos filtráveis por risco, com ação e justificativa |
| Top arquivos | 40 maiores arquivos individuais |
| Idade por ano | Distribuição temporal dos arquivos |

**Ordem sugerida de limpeza:** candidatos **Seguro** → **Cuidado** (após confirmar que não usa) → revisar **Não tocar** manualmente.

## Estrutura do projeto

```
disk_audit.py                  # Script principal
disk_dashboard_template.html   # Template Jinja2 + Chart.js
scripts/validate_csv.py        # Validação do CSV
run.bat                        # Atalho Windows (instala + gera + abre)
requirements.txt               # pandas, jinja2
.cursor/skills/disk-audit/     # Especificação para agentes Cursor
```

Arquivos locais (não versionados): `disk.csv`, `disk_report.html`.

## Privacidade

O CSV e o relatório contêm caminhos e nomes de arquivos do seu sistema. Ambos estão no `.gitignore` — **não faça commit** desses arquivos.

## Estender a ferramenta

Para adicionar regras de detecção, padrões ou alterar o dashboard, consulte:

- `.cursor/skills/disk-audit/SKILL.md` — especificação do projeto
- `.cursor/skills/disk-audit/examples.md` — exemplos práticos
- `.cursor/skills/disk-audit/reference.md` — lista completa de regras e rationales

## Licença

Uso pessoal. Sem garantias.
