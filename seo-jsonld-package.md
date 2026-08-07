# JSON-LD (Structured Data) — pacote para statsfut.com

> Objetivo: rich results no Google (eventos esportivos, times, sitelinks, migalhas).
> Regra: o JSON-LD **nunca pode inventar dado** — só usar informações reais da página (data, times, liga).
> Multilíngue: usar a URL da **versão atual** do idioma e `inLanguage` correspondente.

---

## 1. WebSite (home / base) — elegível para sitelinks de busca

Colocar no `<head>` da home (ou base.html). Só incluir `SearchAction` se existir página de busca pública (o robots.txt bloqueia `/search/` — verificar antes).

```json
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "StatsFut",
  "url": "https://statsfut.com/",
  "inLanguage": "en",
  "description": "Football statistics, predictions and match analysis"
}
</script>
```

---

## 2. SportsEvent — páginas de jogo (match)

No template `match_detail.html`. Usar data/hora reais do jogo. Se não houver estádio, **omitir** `location`.

```json
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SportsEvent",
  "name": "{{ home_team }} vs {{ away_team }}",
  "url": "{{ request.build_absolute_uri }}",
  "startDate": "{{ match.date|date:'c' }}",
  "eventStatus": "https://schema.org/EventScheduled",
  "homeTeam": { "@type": "SportsTeam", "name": "{{ home_team }}" },
  "awayTeam": { "@type": "SportsTeam", "name": "{{ away_team }}" }
}
</script>
```

---

## 3. SportsTeam — páginas de liga (league_dashboard) e times

```json
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SportsTeam",
  "name": "{{ league.name }}",
  "url": "{{ request.build_absolute_uri }}",
  "sport": "Soccer",
  "memberOf": { "@type": "SportsOrganization", "name": "{{ league.country }}" }
}
</script>
```

---

## 4. BreadcrumbList — migalhas em todas as páginas internas

```json
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "{{ base_url }}/" },
    { "@type": "ListItem", "position": 2, "name": "{{ country }}", "item": "{{ base_url }}/stats/{{ country }}/" },
    { "@type": "ListItem", "position": 3, "name": "{{ league.name }}", "item": "{{ base_url }}/stats/{{ country }}/{{ league.slug }}/" }
  ]
}
</script>
```

---

## Como implementar (padrão Django)

1. Em `base.html`, adicionar no `<head>`:
   ```html
   {% block structured_data %}{% endblock %}
   ```
2. Em cada template de página, preencher o bloco com o JSON-LD correspondente.
3. Validar cada tipo no https://validator.schema.org/ (ou Rich Results Test do Google) antes do deploy.

## Checklist de validação
- [ ] JSON-LD bate com o conteúdo visível (nada inventado)
- [ ] URLs apontam para a versão de idioma atual da página
- [ ] `inLanguage` correto por idioma
- [ ] Sem JSON-LD duplicado na mesma página
