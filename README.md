# Disk Audit

[![CI](https://github.com/GuilhermeRoesler/DiskAudit/actions/workflows/ci.yml/badge.svg)](https://github.com/GuilhermeRoesler/DiskAudit/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Auditoria de disco **determinística** (sem IA) a partir de export CSV do [WinDirStat](https://windirstat.net/). Gera um dashboard HTML interativo com KPIs, gráficos e um plano de ação classificado por risco — tudo em português.

> **Atenção:** a ferramenta apenas **recomenda** ações. Nenhum arquivo é deletado automaticamente.

![Dashboard — KPIs e resumo executivo](docs/images/dashboard-hero.png)

![Dashboard — plano de ação com candidatos por risco](docs/images/dashboard-candidates.png)

## Por que este projeto

Disco cheio é um problema recorrente em máquinas de desenvolvimento (Docker, WSL, caches, `node_modules`, modelos LLM). Em vez de apagar “no feeling”, este projeto transforma um snapshot do WinDirStat em um **relatório acionável**: detecta candidatos, classifica risco e explica o porquê.

Demonstra:

- Pipeline de dados tipado (pandas + regras declarativas)
- UX de relatório (Chart.js, filtros, sort, empty states)
- Engenharia defensiva (validador de CSV, privacidade no `.gitignore`, testes)

**Demo anonymizada:** abra [examples/demo_report.html](examples/demo_report.html) no navegador (Chart.js via CDN).

## O que faz

- Lê um snapshot do WinDirStat e detecta automaticamente a unidade e o perfil de usuário
- Identifica candidatos a limpeza (Lixeira, Temp, caches, Docker, WSL, jogos, etc.)
- Classifica cada item em **Seguro**, **Cuidado** ou **Não tocar**
- Exibe distribuição por pastas raiz, AppData e padrões conhecidos
- Lista os maiores arquivos, idade por ano e top extensões

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
# ou: pip install -e .

python scripts/validate_csv.py disk.csv   # opcional, recomendado
python disk_audit.py disk.csv
# após pip install -e .: disk-audit disk.csv
```

Abra `disk_report.html` manualmente se não usar `run.bat`.

## Uso avançado

```bash
# CSV e saída em caminhos customizados
python disk_audit.py "D:\exports\scan.csv" -o "D:\reports\auditoria.html"

# Diretório alternativo do template
python disk_audit.py disk.csv -t . -o test_report.html

# Regenerar o demo do portfólio
python disk_audit.py tests/fixtures/sample.csv -o examples/demo_report.html
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

```bash
python scripts/validate_csv.py disk.csv
```

Retorna exit code `0` se OK, `1` se inválido.

## Relatório gerado

| Seção | Conteúdo |
|-------|----------|
| KPIs | Total em uso, arquivos, % em Users, GB recuperáveis |
| Resumo executivo | Principais oportunidades em linguagem natural |
| Gráficos | Pastas raiz, AppData Local/Roaming, padrões detectados |
| Plano de ação | Candidatos filtráveis por risco, com ação e justificativa |
| Top arquivos | Maiores arquivos individuais |
| Idade por ano | Distribuição temporal dos arquivos |

**Ordem sugerida de limpeza:** candidatos **Seguro** → **Cuidado** (após confirmar que não usa) → revisar **Não tocar** manualmente.

## Testes e qualidade

```bash
pip install -r requirements.txt
pip install ruff   # ou: pip install -e ".[dev]"

python -m unittest discover -s tests -v
ruff check .
```

A CI no GitHub Actions roda lint (Ruff) e testes em Python 3.10 / 3.12 / 3.13.

## Estrutura do projeto

```
disk_audit.py                  # Script principal
disk_dashboard_template.html   # Template Jinja2 + Chart.js
scripts/validate_csv.py        # Validação do CSV
run.bat                        # Atalho Windows (instala + gera + abre)
requirements.txt               # Dependências runtime
pyproject.toml                 # Empacotamento + Ruff + entry point disk-audit
examples/demo_report.html      # Demo anonymizada
docs/                          # Exemplos, referência e imagens do README
tests/                         # Unittest + fixture CSV
.github/workflows/ci.yml       # CI
```

Arquivos locais (não versionados): `disk.csv`, `disk_report.html`.

## Privacidade

O CSV e o relatório contêm caminhos e nomes de arquivos do seu sistema. Ambos estão no `.gitignore` — **não faça commit** desses arquivos. O demo em `examples/` usa apenas dados sintéticos (`TestUser`).

## Documentação

- [docs/examples.md](docs/examples.md) — fluxos, extensão de regras, troubleshooting
- [docs/reference.md](docs/reference.md) — regras, padrões e rationales
- [examples/README.md](examples/README.md) — como regenerar o demo

## Licença

[MIT](LICENSE) © Guilherme Roesler
