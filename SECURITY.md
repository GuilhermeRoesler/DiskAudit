# Política de segurança

## Relatar uma vulnerabilidade

Se encontrar um problema de segurança neste repositório, **não abra uma issue pública**.

Envie um e-mail para o mantenedor via o perfil GitHub do autor do projeto, ou use a aba **Security → Advisories** do repositório, se disponível.

Inclua:

- Descrição do impacto
- Passos para reproduzir
- Versão / commit afetado

## Escopo

Este projeto **não apaga arquivos**. Ele apenas lê CSV do WinDirStat e gera HTML.

Riscos relevantes:

- Exposição acidental de caminhos pessoais em CSV/HTML commitados
- XSS se um template customizado renderizar dados sem escape

## Privacidade

CSV e relatórios reais estão no `.gitignore`. Use apenas fixtures sintéticos (`TestUser`) em PRs e demos.
