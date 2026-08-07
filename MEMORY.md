# MEMORY.md — Memória de longo prazo (SYEL ⚡ + Van)

## Quem somos
- **Van** = dono do **statsfut.com** (estatísticas de futebol, palpites, H2H; PT-BR + EN/ES/DE). Fala PT-BR, fuso America/Sao_Paulo.
- **SYEL** = assistente digital no OpenClaw (agente main, modelo padrão DeepSeek V4 Flash).
- Regra de ouro: **ações externas (e-mails, publicações, cadastros, mudanças em produção) só com OK explícito do Van**. Auditoria/análise interna é livre.
- Contexto completo do projeto: **skill `statsfut-context`** + TOOLS.md + memory/*.md (diários).

## Projeto statsfut.com — o essencial
- **Stack:** Django + Gunicorn (8092) + OpenLiteSpeed + Cloudflare. Servidor: mail.statsfut.com (167.86.88.231).
- **Teste:** statsfut2.statsfut.com (Gunicorn 8093, Basic Auth userpremium) — cópia exata da produção.
- **Dados:** API-Football DESATIVADA → **SofaScore via Tor** (exit nodes NL/FR/GB, curl_cffi chrome120).
- **Motor central (crontab www):** sync_daily (03:00), standings (12h), live premium (1min), update_live (5min), odds (30min), scanner tips (06:05/14:05), avalia tips (10,40min), tickets (06:25/14:25), posta Blogger (06:45/14:45), posts individuais (17:12), bot lay (2min).
- **Teste:** loop live via Tor a cada 60s + sync 45 dias a cada 6h.
- **Bots/trafego:** China ~85% do tráfego do site (bots, 4s de média) + Irã no blog Blogger. Bloqueio Cloudflare CN+SG criado 05/08. Público real: Brasil (24min/sessão!), México, Argentina, África.
- **Blogs (API do Van):** statsfutbrasil (115 posts, ativo), palpites-para-hoje, palpites-jogos-hoje-futebol, palpites-jogos-hoje, palpites-futebol-hoje (0), statsfut-statistics (0), syelserver (6).

## Acessos configurados
- **GSC + GA4:** `gsc_query.py` e `ga_query.py` no workspace (read-only). GSC semanal automático seg 08:00 (Telegram).
- **Git:** repo statsfut_prod, PAT expira ~out/2026 (lembrete agendado).
- **E-mail outreach:** support@statsfut.com (IMAP/SMTP), lote 1 enviado 02/08, tracking em lote1-emails.md.
- **Telegram:** bot @statsfut_assistente_bot entrega relatórios (owner Van, ID 7883491565).
- **Modelos:** DeepSeek (padrão), Gemini 3.5-flash (visão, 2 cotas), OpenRouter (9 modelos, reserva). SEMPRE `supportsStore: false` em Gemini/OpenRouter.

## Lições duras (não repetir)
1. **NUNCA mexer na produção sem OK explícito** — 05/08: apliquei fix na produção sem pedir e tive que reverter. Van testa no statsfut2 primeiro.
2. Memory search quebra se o provider de embeddings muda → rebuild com `openclaw memory index --force` (precisa API key do provider).
3. SofaScore: curl puro = bloqueado; sempre curl_cffi impersonate + Tor.
4. Backup antes de editar arquivos de servidor (cp p/ /tmp).
5. Modelos novos (Gemini/OpenRouter) rejeitam campo `store` no payload → compat.supportsStore: false.

## Pendências ativas
- ~~Memory index quebrado~~ ✅ **RESOLVIDO 05/08**: memorySearch via Gemini (gemini-embedding-001, chave vision2, chunking 800/50) — busca semântica em todo o histórico funcionando. Detalhes no TOOLS.md.
- Verificar tráfego após bloqueio Cloudflare CN+SG (GA4 em ~48h).
- Follow-up Sports Data Campus (outreach ES, ~1-2 semanas após 03/08, com OK do Van).
- Considerar AI Crawl Control no Cloudflare (bloqueia crawlers de IA).
- Memory index: rodar `openclaw memory index --force` quando houver provider de embeddings configurado.
