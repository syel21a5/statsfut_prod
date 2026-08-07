# Auditoria statsfut.com — 01/08/2026

> Auditoria técnica de SEO e performance, nível HTTP + análise de HTML.
> Site: https://statsfut.com (EN padrão + /pt-br/ + /es/ + /de/)

## Resumo executivo

**Veredito: base sólida.** Stack rápida, hreflang corretíssimo, conteúdo realmente traduzido, metadados bons. O site "anda" — falta destravar as **~4.700 páginas de idioma fora do sitemap** e o **structured data**, que é o maior ganho rápido. Performance de servidor excelente (TTFB ~100ms via Cloudflare); o peso do HTML e a falta de lazy loading são os riscos de Core Web Vitals.

---

## ✅ O que está bom (manter)

| Item | Status |
|---|---|
| TTFB | ~100ms (Cloudflare cache HIT) em EN/ES/DE/PT |
| HTTP/2 + HTTP/3 | ✅ |
| Headers de segurança | ✅ X-Frame-Options, nosniff, referrer-policy, COOP |
| hreflang | ✅ Completo: 4 idiomas + x-default, em todas as páginas testadas |
| content-language + `<html lang>` | ✅ Correto por idioma |
| canonical | ✅ Presente (inclusive na www → apex) |
| Conteúdo traduzido de verdade | ✅ /pt-br/ tem texto em português real (não é só label) |
| Title + meta description | ✅ Em home, páginas de liga e páginas H2H |
| 1 H1 por página | ✅ |
| robots.txt | ✅ Bloqueia crawlers de IA, libera buscadores |
| 404 correto + redirects 301 (http→https, trailing slash) | ✅ |
| viewport mobile | ✅ |

---

## 🔴 P0 — Corrigir primeiro (impacto alto, esforço baixo)

### 1. Sitemap sem variantes de idioma (~4.700 páginas fora do mapa)
- Sitemap atual: **1.579 URLs, todas EN** (1.049 stats + 526 match + 4 utilitárias).
- As versões `/pt-br/`, `/es/`, `/de/` **existem** (HTTP 200, conteúdo traduzido) mas **não estão no sitemap**.
- Potencial total: **~6.300 URLs** (1.579 × 4).
- **Fix:** gerar o sitemap com as 4 variantes de cada URL (Google aceita no mesmo arquivo; ou 1 sitemap por idioma). Enviar no Search Console.
- **Ganho:** indexação das páginas PT/ES/DE acelerada — cada idioma rankeia no seu Google local.

### 2. Zero structured data (JSON-LD)
- Nenhuma página testada (home, liga, H2H) tem JSON-LD.
- Para site de stats de futebol, schema recomendado:
  - **WebSite + SearchAction** (home) — elegível para sitelinks de busca
  - **SportsEvent** (páginas de jogos/H2H) — rich results de eventos esportivos
  - **SportsTeam** (páginas de times/ligas)
  - **ItemList / BreadcrumbList** (listas de jogos, migalhas)
- **Ganho:** CTR maior no Google com rich results.

---

## 🟠 P1 — Impacto médio

### 3. Titles/metas das versões de idioma ainda em inglês
- Ex.: `/pt-br/stats/brazil/brasileirao/` tem title **"Brasileirão (Brazil) - Statistics & Match Analysis | StatsFut"** e o conteúdo embaixo em português.
- O Google mostra o title EN para buscas em PT — perde rankeamento em "estatísticas brasileirão", "tabela brasileirão" etc.
- **Fix:** templates traduzem title + meta description por idioma (ex.: "Brasileirão – Estatísticas, Tabela e Análises | StatsFut").

### 4. 198 imagens na home, nenhuma com `loading="lazy"`
- Todas as `<img>` carregam eager → pesa no mobile (LCP/INP).
- **Fix:** `loading="lazy"` nas imagens abaixo da dobra + `width`/`height` para evitar CLS.

### 5. HTML ~510KB por página
- Home, liga e H2H todas em ~510-530KB. Para mobile é pesado.
- **Fix:** diferir scripts inline (GTM/AdSense/Ezoic já são async — verificar o que mais dá pra adiar), dados de matches servidos via JSON sob demanda, minificar.

### 6. Ezoic + AdSense + GTM simultâneos
- Ezoic é conhecido por impactar Core Web Vitals. Não consegui medir CWV real agora (API do PSI sem chave = quota esgotada).
- **Fix:** rodar PageSpeed Insights/Lighthouse (mobile) e medir o impacto real; ajustar configuração do Ezoic se LCP/INP estiverem ruins.

---

## 🟡 P2 — Polimento

### 7. www não redireciona para apex
- `https://www.statsfut.com/` → 200 (canonical aponta para apex, então risco baixo). 301 limpo é melhor.
- **Fix:** redirect 301 www → apex no servidor/Cloudflare.

### 8. Página 404 genérica ("Not Found")
- **Fix:** 404 customizada com busca + links para ligas populares (reduz bounce de visitante perdido).

### 9. Duas regras `User-agent: *` no robots.txt
- Funciona (a segunda sobrescreve/complementa), mas consolidar deixa mais limpo e evita confusão.

---

## ⚠️ Não medido (limitações desta auditoria)

| Item | Como medir |
|---|---|
| Indexação real no Google | Search Console (propriedade statsfut.com) — cadastro pendente |
| Core Web Vitals reais (LCP/INP/CLS) | PageSpeed Insights / Lighthouse (mobile) — rodar manualmente ou com chave de API |
| Perfil de backlinks atual | Ahrefs / Semrush / GSC (links externos) |
| Posições por keyword | GSC ou rank tracker |

---

## 🎯 Plano de ação recomendado (ordem de execução)

1. **Sitemap multilíngue** (~6.300 URLs) + envio no Search Console
2. **JSON-LD** nas páginas (WebSite, SportsEvent, SportsTeam, BreadcrumbList)
3. **Traduzir titles/metas** por idioma (templates)
4. **Lazy loading + dimensões** nas imagens
5. **Reduzir HTML** (diferir, minificar, dados sob demanda)
6. **www → 301 apex** + 404 customizada
7. **Medir CWV real** e ajustar Ezoic se preciso
8. **Cadastros:** Search Console, Bing Webmaster, diretórios de esportes
9. **Keywords por idioma + conteúdo** (mapear buscas de cada mercado)
10. **Backlinks por mercado** (BR, ES, EN, DE)

---

*Gerado por SYEL em 01/08/2026. Auditoria interna — nada foi alterado no site.*
