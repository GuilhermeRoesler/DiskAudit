# Disk Audit — Referência Detalhada

## CANDIDATE_RULES (`diskaudit/rules.py`)

| Regex (resumo) | Risco | Categoria | Ação | min_gb |
|----------------|-------|-----------|------|--------|
| `$Recycle.Bin` | seguro | Lixeira | Esvaziar Lixeira | 0.1 |
| `AppData\Local\Temp` | seguro | Cache | Esvaziar %temp% | 0.5 |
| Opera Software\…\Cache (Local) | seguro | Cache de navegador | Limpar cache Opera | 0.3 |
| Firefox Profiles\…\cache2 (Local) | seguro | Cache de navegador | Limpar cache Firefox | 0.3 |
| Chrome Default\Cache | seguro | Cache de navegador | Limpar cache Chrome | 0.3 |
| npm-cache | seguro | Cache de pacotes | npm cache clean --force | 0.5 |
| pnpm | seguro | Cache de pacotes | pnpm store prune | 0.5 |
| pip\cache | seguro | Cache de pacotes | pip cache purge | 0.5 |
| WinSxS | cuidado | Windows | DISM cleanup | 5.0 |
| .lmstudio\models | cuidado | Modelos LLM | Manter apenas em uso | 5.0 |
| Claude-3p (órfão) | cuidado | App órfão | Deletar após confirmar UWP | 1.0 |
| Docker | cuidado | Dev (Docker) | docker system prune | 2.0 |
| wsl | cuidado | Dev (WSL) | wsl --unregister | 1.0 |
| Android SDK | cuidado | Dev (Android) | SDK Manager cleanup | 2.0 |
| .android\avd | cuidado | Dev (Android) | Remover emuladores | 2.0 |
| .minecraft | cuidado | Jogo | Limpar mods/packs | 3.0 |
| Roblox, CapCut, Steam, Epic, BlueStacks | cuidado | Jogo/Emulador | Variado | 0.5–2.0 |
| Ollama updates_v2 | seguro | Cache de updater | Deletar updates_v2/ | 0.5 |
| Music, Videos, Pictures, Documents | nao_tocar | Pessoal | Backup/revisar | 2.0–5.0 |
| pagefile.sys, hiberfil.sys | nao_tocar | Sistema | Não mexer | 0.1 |

Regras `nao_tocar` só aparecem se o path estiver **dentro do perfil detectado**.

## PATTERNS (gráfico de padrões)

WinSxS, Downloads, AppData\Local\Packages, $Recycle.Bin, wsl, AppData\Local\Programs, Docker, node_modules, Temp, Steam, .cache, .vscode, AppData\Roaming\Code, .gradle, Epic Games, Installer, npm-cache, Logs, Chrome/Firefox/Opera Cache, Chrome User Data, Discord, .m2, OneDrive, WebCache.

## RATIONALE_FNS

| Chave | Função | Contexto extra |
|-------|--------|----------------|
| recycle | Lixeira | Contagem de arquivos |
| temp | Temporários | — |
| browser_cache | Cache navegador | Tamanho + arquivos |
| npm_cache | npm/pnpm/pip | Busca caches relacionados |
| winsxs | Component store | Comando DISM |
| llm_models | LM Studio | Top 5 arquivos .gguf |
| orphan_claude | Claude legado | UWP + vhdx duplicados |
| downloads_zip | Zips em Downloads | Contagem + data mais antiga |
| node_modules | Agregado NM | Top 6 projetos |
| docker | Docker | Tamanho docker_data.vhdx |
| wsl | WSL | Lista ext4.vhdx |
| android / avd | Android dev | — |
| minecraft | Minecraft | Arquivos + GB |
| updater | Instaladores stale | Nomes + total |
| dist | Build artifact | Nome do projeto pai |
| personal | Dados pessoais | — |
| system | Arquivo sistema | — |
| generic | Fallback | GB + arquivos |

## Funções de agregação

| Função | Retorno |
|--------|---------|
| `compute_level2` | Pastas imediatas sob raiz, ordenadas por GB |
| `compute_appdata_children` | Filhos diretos de Local/Roaming (≥0.1 GB) |
| `compute_top_files` | Top N arquivos individuais (default 40) |
| `compute_years` | GB e contagem por ano de modificação |
| `compute_extensions` | Top N extensões por GB (default 20) |
| `compute_patterns` | Soma GB por padrão com dedup de anchors |
| `compute_tier_totals` | Soma GB por nível de risco |

## Template — seções do dashboard

1. KPIs: total, arquivos, % Users, recuperação segura, com cuidado
2. Resumo executivo (HTML injetado)
3. Gráficos: level2, AppData Local, AppData Roaming, padrões
4. Tabela de candidatos (filtro + sort)
5. Top 40 arquivos (filtro + sort)
6. Idade por ano (gráfico)
7. Extensões (details colapsável)

## Export WinDirStat

No WinDirStat: após scan completo, exportar lista para CSV. Garantir encoding UTF-8 e colunas em português (configuração regional do WinDirStat).
