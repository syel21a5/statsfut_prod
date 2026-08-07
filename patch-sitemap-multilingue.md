# PATCH — Sitemap multilíngue (statsfut.com)

Arquivo a alterar: `matches/templates/matches/sitemap.xml`
(gerado pela view `SitemapView` em `matches/views.py` — nenhuma mudança necessária na view)

## Mudança 1 — namespace xhtml no `<urlset>`

De:
```xml
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
```
Para:
```xml
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
```

## Mudança 2 — Home com alternates de idioma

Dentro do bloco `<url>` da home (`<loc>{{ base_url }}/</loc>`), adicionar após o `<loc>`:
```xml
    <xhtml:link rel="alternate" hreflang="en" href="{{ base_url }}/" />
    <xhtml:link rel="alternate" hreflang="pt-br" href="{{ base_url }}/pt-br/" />
    <xhtml:link rel="alternate" hreflang="es" href="{{ base_url }}/es/" />
    <xhtml:link rel="alternate" hreflang="de" href="{{ base_url }}/de/" />
    <xhtml:link rel="alternate" hreflang="x-default" href="{{ base_url }}/" />
```

## Mudança 3 — Loop de ligas com alternates

De:
```xml
{% for url in league_urls %}
<url>
    <loc>{{ base_url }}{{ url }}</loc>
```
Para:
```xml
{% for url in league_urls %}
<url>
    <loc>{{ base_url }}{{ url }}</loc>
    <xhtml:link rel="alternate" hreflang="en" href="{{ base_url }}{{ url }}" />
    <xhtml:link rel="alternate" hreflang="pt-br" href="{{ base_url }}/pt-br{{ url }}" />
    <xhtml:link rel="alternate" hreflang="es" href="{{ base_url }}/es{{ url }}" />
    <xhtml:link rel="alternate" hreflang="de" href="{{ base_url }}/de{{ url }}" />
    <xhtml:link rel="alternate" hreflang="x-default" href="{{ base_url }}{{ url }}" />
```

## Mudança 4 — Loop de jogos (matches) com alternates

Mesma alteração do loop de ligas no `{% for url in match_urls %}`.

## NÃO alterar

- Blocos de `privacy-policy`, `terms-of-use`, `about-us` (não têm versão traduzida confirmada)
- Loop de teams (`team_urls`) — páginas de time nos outros idiomas **não confirmadas**; deixar como está
- URLs, prioridades, changefreq

## Teste após deploy

```bash
# Validar XML e conferir hreflang
curl -s https://statsfut.com/sitemap.xml | head -40
curl -s https://statsfut.com/sitemap.xml | grep -c "xhtml:link"   # deve ser > 0
```
Depois: reenviar o sitemap no Google Search Console (cada propriedade de idioma).

## Referência

Arquivo gerado de exemplo (1.577 URLs base com alternates): `sitemap-multilang.xml`
(no workspace do SYEL — serve de referência para conferência, mas o correto é o patch acima para gerar dinamicamente)
