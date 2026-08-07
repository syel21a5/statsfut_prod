# USER.md - About Your Human

- **Name:** Van
- **What to call them:** Van
- **Pronouns:** _(não informado)_
- **Timezone:** America/Sao_Paulo (GMT-3)
- **Notes:** Fala português (BR). Site: **statsfut.com** — estatísticas de futebol, previsões e análise de confrontos (H2H), conteúdo em PT-BR. Quer fazer o site "voar".

## Site — statsfut.com

- **Nicho:** estatísticas/palpites de futebol (ligas do mundo todo, foco BR + principais ligas).
- **Stack:** Cloudflare CDN + LiteSpeed, HTTP/2 e HTTP/3, headers de segurança bons.
- **Sitemap:** 1.579 URLs, bem organizado (stats/<país>/<liga>).
- **robots.txt:** bloqueia crawlers de IA (GPTBot, ClaudeBot etc.), permite buscadores.
- **Multilíngue (feito certo):** 4 idiomas com URLs próprias — `/` (EN, x-default), `/pt-br/`, `/es/`, `/de/` — cada uma com header `content-language` + `<html lang>` corretos e hreflang completo (4 idiomas + x-default). Switch por flags. Nada de bug aqui (o `content-language: en` era só a home ser inglês mesmo).

## Context

- Projeto principal: melhorar performance, SEO e visibilidade do site.
- Interessado em: cadastros (Google Business Profile, diretórios), backlinks legítimos (nada de esquema de link em massa), conteúdo otimizado.
- Regra combinada: ações externas (e-mails, publicações, cadastros) só com OK dele; auditorias e análise interna posso fazer à vontade.
