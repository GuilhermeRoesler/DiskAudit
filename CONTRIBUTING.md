# Contribuindo

Obrigado pelo interesse em melhorar o Disk Audit.

## Ambiente

```bash
pip install -e ".[dev]"
```

## Antes de abrir um PR

```bash
ruff check .
mypy
python -m unittest discover -s tests -v
coverage run -m unittest discover -s tests -v
coverage report
```

Opcional (hooks locais):

```bash
pip install pre-commit
pre-commit install
```

## Adicionar uma regra de candidato

1. Declare a regra em `diskaudit/rules.py` (`CANDIDATE_RULES`)
2. Se precisar de texto específico, implemente em `diskaudit/rationales.py` e registre em `RATIONALE_FNS`
3. Inclua caminhos sintéticos em `tests/fixtures/sample.csv` (use `TestUser`, sem dados reais)
4. Adicione um assert em `tests/test_disk_audit.py`
5. Regenerar o demo se o relatório mudar:

```bash
python -m diskaudit.cli tests/fixtures/sample.csv -o examples/demo_report.html
```

## Escopo

- Minimize mudanças; mantenha a stack em pandas + Jinja2
- Não integre IA e não delete arquivos automaticamente
- Não faça commit de `disk.csv` / relatórios reais

## Commits

Mensagens curtas no estilo do repositório (imperativo, foco no *porquê*).
