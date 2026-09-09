# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere a [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.1.1] — 2026-09-08

### Adicionado

- Validação do CSV integrada à CLI (flag `--no-validate` para pular)
- Tipagem `Candidate`, `ReportData` e `RiskLevel` no pacote
- Detecção de `dist/` baseada apenas no CSV (marcadores `package.json` / `src`)

### Alterado

- Regra Ollama aponta para `updates_v2/` (não a pasta inteira do app)
- `scripts/validate_csv.py` reutiliza `diskaudit.validate`

### Corrigido

- Escape de HTML no resumo executivo (paths vindos do CSV)

## [1.1.0] — 2026-09-08

### Adicionado

- Chart.js empacotado em `diskaudit/static/` (relatórios HTML self-contained / offline)
- Meta viewport, Open Graph/Twitter, labels e ordenação por teclado no dashboard
- Footer com link do repositório e versão do pacote
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` e issue templates
- Dependabot, pre-commit, workflow de publish no PyPI e upload Codecov
- Fixture expandido (WSL, LLM, Android, Minecraft, pagefile, downloads ZIP, etc.)
- Testes de CLI, rationales e resumo executivo
- Script `scripts/generate_demo.py` para regenerar o relatório demo

### Alterado

- Dashboard: “Não tocar” em slate, fundo sutil, zebra na tabela e hierarquia mais clara no plano de ação
- GitHub Pages gera o demo a partir do fixture a cada deploy (sem drift)
- `run.bat` instala com `pip install -e .`, valida o CSV e chama a CLI
- Filtro de perfil `nao_tocar` aplica-se apenas a conteúdo pessoal (não a pagefile/sistema)

### Corrigido

- Candidatos de sistema na raiz do disco (`pagefile.sys`) voltam a aparecer no plano de ação

## [1.0.1] — 2026-09-08

### Corrigido

- Parse de paths WinDirStat com `PureWindowsPath` (CI Linux)
- Type-check estável na CI sem conflito de stubs NumPy/pandas

## [1.0.0] — 2026-09-08

### Adicionado

- Pacote instalável `diskaudit` com módulos `analyze`, `candidates`, `rules`, `rationales`, `render`, `cli`
- Template HTML empacotado em `diskaudit/templates/`
- Demo pública via GitHub Pages
- CI com Ruff, mypy e coverage
- Testes de borda (CSV inválido, fallback de raiz, render)
- `CHANGELOG.md` e metadados prontos para publicação no PyPI

### Alterado

- Entry point `disk-audit` aponta para `diskaudit.cli:main`
- `disk_audit.py` permanece como shim de compatibilidade
- README com demo ao vivo, diagrama de fluxo, blurb em inglês e números do fixture

### Segurança / privacidade

- CSV e relatórios reais continuam fora do versionamento (`.gitignore`)

[1.1.0]: https://github.com/GuilhermeRoesler/DiskAudit/releases/tag/v1.1.0
[1.0.1]: https://github.com/GuilhermeRoesler/DiskAudit/releases/tag/v1.0.1
[1.0.0]: https://github.com/GuilhermeRoesler/DiskAudit/releases/tag/v1.0.0
