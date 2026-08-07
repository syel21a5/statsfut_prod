---
name: "statsfut-context"
description: "Contexto completo do projeto statsfut.com: infra, cron, Tor/SofaScore, acesso a dados e lições aprendidas. Leia ao iniciar qualquer conversa sobre o site."
---

# Skill: statsfut-context

Manual de bordo do projeto **statsfut.com** — leia este arquivo quando o usuário (Van) pedir qualquer coisa sobre o site, os servidores, cron jobs, tráfego, SEO ou bots. Ele existe para que QUALQUER modelo de IA (DeepSeek, GPT, Qwen, Llama, etc.) se situe em segundos, mesmo sem histórico de conversa.

## Quem é o usuário
- **Van** — dono do site statsfut.com (estatísticas de futebol, palpites, H2H, PT-BR + EN/ES/DE).
- Fala português (BR). Timezone: America/Sao_Paulo.
- Regra combinada: **ações externas (e-mails, publicações, cadastros, mudanças em produção) só com OK explícito dele**. Auditoria/análise interna é livre.
- Objetivo atual: fazer o site "voar" (SEO, performance, visibilidade) e resolver tráfego bot.

## Stack e infraestrutura
- **Servidor:** VPS Linux (host: mail.statsfut.com), IP 167.86.88.231.
- **Web:** OpenLiteSpeed (logs em /www/wwwlogs/*_ols.access_log) + Cloudflare CDN na frente (NS: bryce/eve.ns.cloudflare.com).
- **App:** Django (`/www/wwwroot/statsfut.com`), Gunicorn porta 8092, 3 workers, service systemd `statsfut.service`.
- **Site de teste:** statsfut2.statsfut.com (`/www/wwwroot/statsfut2.statsfut.com`), Gunicorn porta 8093, 2 workers, service `statsfut2-gunicorn.service`. Cópia exata da produção, com Tor no lugar da API-Football. Basic Auth: user `userpremium` / senha em TOOLS.md.
- **Banco:** MySQL/MariaDB via aaPanel. Tabelas principais: matches (65k+), teams, leagues, seasons, goals, standings.
- **Painel:** aaPanel/BT Panel (banco interno: /www/server/panel/data/default.db, tabela `crontab`).

## Fonte de dados de futebol
- **API-Football:** DESATIVADA globalmente (`APIManager.USE_API_FOOTBALL = False`) — chave paga fora do ar/evitada.
- **SofaScore via Tor:** fonte principal atual. SofaScore bloqueia IP de datacenter (403); passa via Tor com exit nodes só de NL/FR/GB (`/etc/tor/torrc`: `ExitNodes {nl},{fr},{gb}` + `StrictNodes 1`).
- Tor roda como serviço systemd (`tor@default.service`), SOCKS 127.0.0.1:9050, ControlPort 9051. Rotacionar circuito: `systemctl reload tor`.
- Cliente HTTP obrigatório: `curl_cffi` com `impersonate="chrome120"` (curl puro é bloqueado por fingerprint). Código em `matches/services/sofascore_tor.py`.
- Endpoint de jogos futuros (ATUALIZADO 08/2026): `unique-tournament/{id}/season/{sid}/events/next/{pagina}` (o antigo `scheduled-events/{data}` foi descontinuado, 404).
- Mapa completo de ligas: `SOFA_LEAGUE_IDS` em sofascore_tor.py cobre as 49 ligas do banco (IDs validados). `league_map` em update_live_matches.py traduz nomes do SofaScore → banco. Brasileirão canônico: Série A=2, B=70, C=71 (duplicatas 85/86/87/88 removidas).

## Cron jobs (crontab do usuário www — MOTOR CENTRAL)
Rodam em `/www/wwwroot/statsfut.com` com o venv:
| Frequência | Comando | Função |
|---|---|---|
| 03:00 diário | `sync_daily_api` | Maestro diário (API-Football — atualmente aborta, desativada) |
| a cada 12h | `recalculate_standings --smart` | Tabelas de classificação |
| a cada 1min | `live_score_premium` | Robô ao vivo premium |
| a cada 5min | `update_live_matches --mode both` | Escudo gratuito: atualiza jogos |
| a cada 30min | `import_odds_api_fixtures --league ALL` | Cotações/odds |
| 06:05 e 14:05 | `generate_scanner_tips` | Gera tips do scanner |
| 10,40 min | `evaluate_scanner_tips` | Avalia tips |
| 06:25 e 14:25 | `generate_tickets` | Expert tickets |
| 06:45 e 14:45 | `post_to_blogger` | Publica no Blogger |
| 17:12 | `post_jogos_individuais` | Posts por jogo (SEO, 24h antes) |
| a cada 2min | `run_live_lay_bot` | Bot Telegram Lay + Under |

**statsfut2 (teste):**
- `loop_live_tor.sh` (service `statsfut2-live.service`): roda `update_live_matches --mode live --force` a cada 60s via Tor.
- `sync_upcoming_tor.sh` (cron `0 */6 * * *`): busca 45 dias de fixtures via Tor (~2.400 jogos, ~12 min).

## Logs importantes
- `/www/wwwroot/statsfut.com/logs/` — cron_*.log (live, odds, blogger, tips etc.)
- `/www/wwwlogs/statsfut.com_ols.access_log` — acessos HTTP produção
- `/www/wwwlogs/statsfut2.statsfut.com_ols.access_log` — acessos teste
- `/usr/local/lsws/logs/access.log` — geral LiteSpeed
- Logs de live/erros do Django: `logs/django_errors.log`, `logs/live_tor.log`

## Acesso a dados (Google) — workspace do OpenClaw
Scripts em `/root/.openclaw/workspace/` (credenciais em `.secrets/`, chmod 600):
- `gsc_query.py [summary|queries|pages|countries|sitemaps] [dias] [limite]` — Google Search Console (cliques/impressões/CTR/posição), read-only. Propriedades: `sc-domain:statsfut.com` + blog.
- `ga_query.py [dias] [summary|pages|sources] [site|blog]` — GA4 (sessões/usuários/pageviews). Property IDs: site=537252454, blog=544305744.
- Análise por país/engajamento no GA4: chamada direta `analyticsdata.googleapis.com/v1beta/properties/{id}:runReport` com dimensão `country` e métricas `sessions`, `engagementRate`, `averageSessionDuration` (ver histórico — engagementRate vem como float 0-1).
- E-mail outreach: `check-mail.py` (IMAP support@statsfut.com), tracking em `lote1-emails.md`, modelo em `modelo-email-outreach.md`. Lotes de 5-10, zero spam, 1º e-mail sempre mostrado antes.

## Git
- Repo: `github.com/syel21a5/statsfut_prod` (servidor `/www/wwwroot/statsfut.com`). Push: `git push origin main`.
- Credencial: fine-grained PAT em `.secrets/github_token` (expira ~out/2026 — avisar Van). Helper em `.secrets/git-credential-github.sh`.

## Telegram
- Bot @statsfut_assistente_bot entrega crons (relatório semanal GSC/GA seg 08:00, lembretes). Owner Van (ID 7883491565). Token em `/root/.openclaw/.secrets/telegram_bot_token`.

## Tráfego bot (situação 05/08/2026)
- **statsfut.com:** ~85% do tráfego vem da China (567 sessões/7d, engajamento 13%, ~4s) + Singapore (56 sessões, 2,4s) = bots/scrapers. Público real: Brasil (51 sessões, 24min, 65% engajamento), México, Canadá, Argentina, África.
- **Blog Blogger (statsfutbrasil):** Irã domina (3.706 sessões/7d) — crawlers/tráfego estranho.
- **Ação tomada (05/08):** Van criou regra manual no Cloudflare WAF: "Bloquear Bots China e Singapura" (Country=CN + Country=SG → Block, Active). AI Crawl Control disponível no painel (item do menu Security).
- Comportamento bot a vigiar: país com muitas sessões, tempo médio <5s, engajamento <20%.

## Home page — filtro de jogos finalizados (IMPORTANTE)
- `HomeView.get_queryset` (matches/views.py) exclui status: `['Finished','FT','AET','PEN','FINISHED','Postponed','PST','AWD','CANC']` — aplicado nos filtros today/tomorrow/next_round e no Palpite do Dia.
- **05/08/2026:** esse fix foi aplicado na PRODUÇÃO por engano (Van só tinha pedido no statsfut2) e **REVERTIDO** no mesmo dia (commit revert 7750831). A produção NÃO tem o filtro; o statsfut2 TEM. **Não mexer na produção sem OK explícito.**
- Cache da home (statsfut2): `{% cache cache_timeout home_matches ... %}` — timeout 60s sem live, 0 com live (arquivo /tmp/statsfut_cache). Home em pt-BR tem cache separado do EN (LANGUAGE_CODE no cache key).
- Ao diagnosticar "jogo finalizado na home": checar banco (status dos jogos de hoje), cache Django, e lembrar que jogos que terminaram de madrugada podem aparecer com placar até o loop live marcar FT + cache expirar.

## Lições aprendidas (não repetir)
1. **Nunca mexer na produção (statsfut.com) sem OK explícito do Van** — mesmo que o bug seja óbvio. Ele testa no statsfut2 primeiro.
2. Gemini/OpenRouter: modelos novos precisam de `compat.supportsStore: false` (API rejeita campo `store`).
3. Memory search pode quebrar quando o provider de embeddings muda — rebuild via `openclaw memory index --force` (precisa de API key do provider configurado).
4. SofaScore: nunca usar curl puro; sempre curl_cffi + Tor.
5. Sempre fazer backup antes de editar arquivos do servidor (cp para /tmp).

## Fluxo recomendado ao receber pedido sobre o site
1. Identificar se é produção (statsfut.com) ou teste (statsfut2) — confirmar com Van se ambíguo.
2. Ver estado atual: logs, banco, cache, serviços (nunca assumir).
3. Propor mudança → esperar OK do Van → aplicar com backup → testar → commitar se for repo git.
4. Responder em PT-BR, tom direto, com números reais.
