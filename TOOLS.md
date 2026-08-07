# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup: camera names and locations, SSH hosts and aliases, preferred TTS voices, speaker/room names, device nicknames, anything environment-specific.

## Google Search Console (statsfut.com) + Blogger

- **Acesso automático via API** (read-only GSC + read/write Blogger): `gsc_query.py` no workspace.
- Credenciais: `.secrets/gsc_client.json` + `gsc_tokens.json` (chmod 600). Client OAuth Desktop, escopos `webmasters.readonly` + `blogger`, projeto `statsfut-gsc`.
- Uso GSC: `python3 gsc_query.py [summary|queries|pages|countries|sitemaps] [dias] [limite]`
- Propriedades GSC: `sc-domain:statsfut.com` + `https://statsfutbrasil.blogspot.com/`.
- Cron GSC: semanal seg 08:00 (id 05d41e89-4f54-455c-9c90-8deca7f575b5).
- **Blogs da conta do Van (API):** statsfutbrasil (115 posts, ativo), palpites-para-hoje (31), palpites-jogos-hoje-futebol (31), palpites-jogos-hoje (31), palpites-futebol-hoje (0), statsfut-statistics (0), syelserver/"Arquivos Syel" (6). statsfutdicas NÃO está nesta conta.
- Token revogável pelo Van em Conta Google → Segurança → Aplicativos de terceiros.

---

## GitHub — repo statsfut_prod (servidor /www/wwwroot/statsfut.com)

- Remote: `https://github.com/syel21a5/statsfut_prod.git` (SEM token na URL).
- Credencial: fine-grained PAT do Van (válido ~90 dias, só repo statsfut_prod, Contents RW) em `.secrets/github_token` (chmod 600).
- Helper de credencial: `.secrets/git-credential-github.sh` (chmod 700), registrado como `credential.helper` no config do repo (não global).
- Expira ~out/2026 → quando o push falhar com auth error, pedir token novo ao Van.
- `git push origin main` funciona localmente agora (15 commits pendentes subiram em 03/08).
- `.gitignore` cobre `.env*` (só `.env.example` versionado).

---

## E-mail de outreach (backlinks)

- Caixa: `support@statsfut.com` — credenciais em `.secrets/support_mail.json` (chmod 600). SMTP 587 STARTTLS + IMAP 993 em mail.statsfut.com.
- Envio aprovado pelo Van em lote; primeiro e-mail sempre mostrado antes de enviar. Modelo em `modelo-email-outreach.md` (PT/EN/ES).
- Lote 1 enviado 02/08: terrordasbets, mantosdofutebol, sportsdatacampus. Tracking: `lote1-emails.md`.
- Regras: zero spam, lotes de 5-10, intervalo entre envios, acompanhar respostas via IMAP.

---

## Tor no servidor (acesso SofaScore)

- **Tor instalado e ativo:** SOCKS `127.0.0.1:9050`, ControlPort 9051 (`CookieAuthentication 0` → sem auth; NEWNYM direto funciona: `printf 'AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT\r\n' | nc 127.0.0.1 9051`).
- **SofaScore bloqueia IPs de datacenter direto** (403 Forbidden) — só passa via Tor com exit node de país "liberado".
- **Países testados (03/08/2026):** ✅ NL, FR, GB passam (HTTP 200) | ❌ US, DE, SE bloqueados (403 challenge).
- **torrc configurado:** `ExitNodes {nl},{fr},{gb}` + `StrictNodes 1` (backup: `/etc/tor/torrc.bak-20260803`). Rotacionar circuito: `systemctl reload tor`.
- **Uso:** `torsocks venv/bin/python proxy_sofascore_fetcher.py --tournament <id> --season <id> [--last-rounds N]` → salva `payload.json` na raiz do projeto. Alternativa: `python manage.py deep_scrape_menu --tor` (stream isolation user:pass@9050).
- **Fingerprint importa:** usar curl_cffi (`impersonate="chrome120"`) ou Playwright; curl puro é bloqueado por fingerprint.
- Playwright 1.58 + Chromium instalados no python do SISTEMA (`/usr/bin/python3`), não no venv.

---

## Memory Search (busca semântica) — CONFIGURADO 05/08 ✅

- **Provider:** gemini (endpoint nativo), modelo `gemini-embedding-001`, chave **vision2** (workspace/.secrets/gemini_keys.json) gravada direto em `agents.defaults.memorySearch.remote.apiKey` no openclaw.json.
- **Chunking:** 800 tokens, overlap 50 (importante: chunking menor gerava batches >50 chunks e o Gemini free dava 429 RESOURCE_EXHAUSTED em batchEmbedContents). `nonBatchConcurrency: 1`.
- Índice: 5/5 arquivos, 52 chunks, vetores 3072d. Rebuild: `openclaw memory index --force --agent main`.
- Lição: batchEmbedContents do Gemini free aceita no máx ~50 chunks/request; texto >~5k chars direto = 429. Endpoint OpenAI-compat (v1beta/openai/embeddings) funciona com texto pequeno mas não com batch grande.

## Gemini (visão/prints) — agente Vision 👁️

- **Provedores config:** `gemini-1` e `gemini-2` (custom, openai-completions) → baseUrl `https://generativelanguage.googleapis.com/v1beta/openai/`, auth profiles `gemini-1:default` e `gemini-2:default` (api_key).
- **Modelos (input text+image):** `gemini-3.5-flash` (primário do agente vision), `gemini-3.6-flash`, `gemini-3-flash-preview`.
- ⚠️ **`gemini-2.5-flash` NÃO funciona em chaves novas** (Google migrou pros 3.x) — usar sempre os 3.x.
- **Chaves:** `workspace/.secrets/gemini_keys.json` (chmod 600) — `vision1` = projeto statsfut-vision-1, `vision2` = projeto statsfut-vision-2. Ambas validadas (04/08).
- **Agente `vision`** criado em `agents.list` (workspace compartilhado): primário `gemini-1/gemini-3.5-flash`, fallbacks → `gemini-2/gemini-3.5-flash` → `gemini-2/gemini-3.6-flash`. Trocar: `/agent vision` no chat. Modelos gemini também disponíveis no agente main via `/model` (alias "Gemini Flash").
- **Teste de visão validado** (04/08): print fake lido corretamente pelas 2 chaves (texto + placar). Print real do canal YouTube lido com sucesso após fix (vídeos, inscritos, banner).
- ⚠️ **BUG IMPORTANTE (04/08):** o tool de imagem do OpenClaw falhava com `400 no body` no Gemini — causa: o transporte mandava `"store": false` no payload (compat auto-detectado como endpoint OpenAI padrão), e a API do Gemini rejeita esse campo. **Fix:** `"compat": {"supportsStore": false}` em TODOS os modelos gemini (e `supportsReasoningEffort: false` no gemini-3-flash-preview). Se um dia adicionar novo modelo/provedor Gemini, lembrar disso!
- **Debug de payload:** `OPENCLAW_DEBUG_MODEL_PAYLOAD=full-redacted` (env do serviço systemd) — não grava no log padrão; pra ver o request real, usar proxy local capturando headers+body (truque usado pra achar o bug).
- **Pendente:** OpenRouter (chave grátis) como reserva extra de visão/texto.
- **Cota grátis = por projeto Google** (não por chave). 2 projetos = 2 cotas. Não criar 6 (risco de ban da conta GSC/Blogger).

## StatsFut2 — site de teste (statsfut2.statsfut.com)

- **URL:** https://statsfut2.statsfut.com
- **Basic Auth (trocaram 04/08):** user `userpremium` | senha `importe*$2010` (é o login do Van; antigo `teste`/`sf29565Xk9` desativado)
- Cópia exata do statsfut.com p/ testes (Tor no lugar da API-Football). Gunicorn porta 8093.
- Banco: `statsfut2` (restaurado do dump 20260801).

---

## Telegram (canal de entrega pro Van)

- Bot: **@statsfut_assistente_bot** ("StatsFut Assistente"), criado por Van via BotFather 03/08.
- Token: `/root/.openclaw/.secrets/telegram_bot_token` (600), referenciado via `tokenFile` na config (channels.telegram).
- dmPolicy: `pairing` — Van pareado (ID 7883491565), aprovado e definido como owner.
- Entrega de crons: GSC semanal (05d41e89) com delivery announce → telegram 7883491565. Cron de reminder do token GitHub (~out/2026) idem.
- Checar pareamentos: `openclaw pairing list telegram` / `openclaw pairing approve telegram <CODE>`.
- Sessões do Telegram são separadas (agent:main:telegram:...) e não aparecem na visibilidade restrita (tree) desta sessão webchat.

---

## Exemplos

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)

## Tor no statsfut2 — endpoint de jogos futuros (ATUALIZADO 04/08)

- ⚠️ **SofaScore descontinuou** `scheduled-events/{data}` (404). Formato atual: `unique-tournament/{id}/season/{sid}/events/next/{page}` (30 eventos/página).
- `get_upcoming_fixtures` em `matches/services/sofascore_tor.py` já corrigido para varrer `SOFA_LEAGUE_IDS` (ampliado com Colômbia, Peru, Chile, Equador B, USL, Eliteserien, Allsvenskan etc.).
- Sync automático de jogos futuros: `sync_upcoming_tor.sh` + cron `0 */6 * * *` (3 dias à frente).
- **Mapa completo de ligas:** SOFA_LEAGUE_IDS em matches/services/sofascore_tor.py cobre as 49 ligas do banco (IDs validados 04/08). league_map em update_live_matches.py traduz nomes atuais do SofaScore → banco.
- **Duplicatas brasileiras removidas** (04/08): ligas 85/86/87/88 deletadas; canônicas: Brasileirão=2, Série B=70, Série C=71.

## OpenRouter (reserva de modelos)

- Chave: `.secrets/openrouter_key` (sk-or-…5446, ativa, tier paga com créditos). Auth profile `openrouter:default`.
- Provider `openrouter` na config: 4 modelos (deepseek-chat, deepseek-r1, llama-3.3-70b, qwen-2.5-72b) com `supportsStore: false`.
- Trocar: `/model openrouter/<id>`. Custo baixo (centavos por 1M tokens).
