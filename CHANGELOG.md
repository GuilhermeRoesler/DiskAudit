# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere a [Semantic Versioning](https://semver.org/lang/pt-BR/).

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

[1.0.0]: https://github.com/GuilhermeRoesler/DiskAudit/releases/tag/v1.0.0
