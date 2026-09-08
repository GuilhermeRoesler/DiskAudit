# Demo

Relatório HTML anonymizado gerado a partir de `tests/fixtures/sample.csv`.

## Abrir

- **Ao vivo:** [guilhermeroesler.github.io/DiskAudit](https://guilhermeroesler.github.io/DiskAudit/)
- **Local:** abra [demo_report.html](demo_report.html) no navegador (Chart.js vem embutido — funciona offline)

## Regenerar

```bash
python -m diskaudit.cli tests/fixtures/sample.csv -o examples/demo_report.html
```

O deploy do GitHub Pages também regenera o HTML a partir do fixture (não depende só deste arquivo versionado).
