# 📌 PRÓXIMOS PASSOS — statsfut.com

> Última atualização: 02/08/2026 (~11:20)

## ✅ CONCLUÍDO E VALIDADO (no ar)
- Títulos + meta descriptions nos 4 idiomas (home, liga, H2H, jogo)
- Sitemap multilíngue com hreflang + reenvio GSC (agora 1.510 URLs — escudo anti-404)
- JSON-LD (WebSite, SportsTeam, SportsEvent)
- Lazy loading + preconnect + 404 customizada
- **M7 (H1s liga/H2H/jogo)** c154262 · **M8 (H1s time/live/estáticas)** aa2aa08 · **M9 (setlang/robots)** 3b3967e
- **M10 (páginas de país)** d5f9232 — H1/title com nome do país, 4 idiomas
- **M11 (sitemap sem 404)** a149480 — escudo anti-404 (resolve+get_object); sitemap 1.562→1.510
- 301 www → apex (Cloudflare Redirect Rules)
- **Acesso GSC via API** (gsc_query.py + tokens) + **cron relatório semanal seg 08:00**
- Dados reais GSC 28d: 35 cliques / 2.874 impressões / CTR 1,2% / pos 34,2

## ✅ MISSÃO 12 — CONCLUÍDA E VALIDADA (02/08 ~11:35)

> Commit 5493143. Redirects automáticos 301 em LeagueDetailView/TeamDetailView (slug canônico + liga correta; reverse() preserva idioma e query string). Validado: /PAYSANDU/ → 301 /paysandu/; /serie-c/flamengo/ → 301 /brasileirao/flamengo/; balde E do GSC: 29/56 agora 301. Restantes: 26 legado /en/ (caem sozinhos) + 1 malformada. **404 do GSC encerrados** (setlang ✅, www ✅, renomeados ✅, legado cai sozinho).
> ⏳ Única pendência 404: decisão do Van sobre matches antigos (balde D, 250 URLs) + regra de retenção (perguntada ao antigravidade).

## ❓ DECISÕES DO VAN
- **Jogos antigos (balde D, 250 URLs):** manter no ar (arquivo histórico, mais impressões) ou deixar apagar? Aguardando regra de retenção do código.
- Blog statsfut.com/blog + blogspot: mexer depois.
- Traduzir nomes de países por idioma (Brasil/Alemanha em PT/DE) — polimento menor.

## ✅ MISSÃO 13 — CONCLUÍDA (02/08 ~11:44)

> Commit 8e898bb. Vilão dos 250 matches mortos: `rebuild_database.py` (linha 17) e `rebuild_league.py` (linha 36) truncavam `Match.objects.all().delete()` → IDs novos → URLs antigas morriam. Fix: rebuilds só apagam jogos NÃO finalizados (protege Finished/FT/AET/PEN); pipeline vira upsert incremental. **Verificação pendente:** rodar um rebuild e confirmar que histórico sobrevive.

## ✅ MISSÃO 14 — CONCLUÍDA 100% (02/08 ~14:45) + MISSÃO 15

> **48 ligas × 4 idiomas com texto introdutório NO AR** (lotes 1-4; fixes meus 0039 e 0043 no matching). Duplicado morto Brasil/Serie A (0 matches) → 301 automático → /brasileirao/ (alias + M12). Sitemap: 1.606 URLs, zero lixo. **Deploy = git pull + migrate + restart statsfut.service** (sem restart o código novo não pega).

## ✅ MISSÃO 16 — CONCLUÍDA (02/08 ~15:03)

> Commit 4f3eb96. Internal linking: match → H2H + times; H2H → times. Validado ao vivo. Mapa de keywords refinado com dados reais (seo-keyword-map.md).

## ✅ MISSÃO 17 — CONCLUÍDA (02/08 ~15:09)

> Commit dde112d. 35 hubs de país × 4 idiomas no ar. **CONTEÚDO 100% COMPLETO (48 ligas + 35 países).**

## 📊 PRÓXIMAS AÇÕES (por valor)
1. **Conteúdo fino** nas páginas de liga/país (~2.300 rastreadas não indexadas) — usar queries reais do GSC
2. **Refinar mapa de keywords** (`seo-keyword-map.md`) com dados reais (BR/ES em destaque)
3. **Internal linking** entre páginas de jogo/H2H/liga
4. Limpar 404 restantes (export GSC analisado: 732 → setlang 202 ✅ resolvidos, www 92 ✅, /en/ 231 e /team/ 17 legados caem sozinhos, match 250 decisão acima, renomeados 30 = M12)
5. Investigar 184 (5xx) — provável do incidente de logs (confirmar que parou)

## 🗂️ PENDÊNCIAS MENORES
- Reduzir HTML de ~500KB (medir com Lighthouse antes)
- Trocar token GitHub embutido no remote por SSH (segurança)
- Decidir: cron de proteção dos logs (chown)?
- Limpeza repo: `temp_test.py` + `video_maker_openclaw.zip` (3,7MB)
- Opcional: 301 /en/ → / (acelera limpeza do balde C no GSC)

## 📂 ARQUIVOS DE REFERÊNCIA
- `audit-statsfut-2026-08-01.md` · `seo-keyword-map.md` · `seo-jsonld-package.md` · `patch-sitemap-multilingue.md` · `gsc_query.py`
- Secrets: `.secrets/gsc_client.json` + `gsc_tokens.json` (chmod 600)
