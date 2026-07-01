# SKILL 15: Gestão e Correção de Logos de Times

## Visão Geral
Nós utilizamos duas abordagens para gerenciar as logos dos times:
1. **TheSportsDB (Automático e Padrão)**: Busca gratuita e automatizada, sem bloqueios de segurança.
2. **SofaScore (Específico e Manual)**: Possui bloqueio Cloudflare (Erro 403), mas tem logos de excelente qualidade e times menores.

## Abordagem 1: TheSportsDB (A Forma Oficial)
Sempre que novos times forem integrados, a primeira tentativa deve ser pelo `TheSportsDB`.

**Script:** `matches/management/commands/fix_logos_sofascore.py` (apesar do nome, ele busca no TheSportsDB).
**Uso:**
```bash
python manage.py fix_logos_sofascore
```
**O que ele faz:**
- Lê todos os times sem logo no banco local.
- Consulta a API gratuita do TheSportsDB (`https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t=NOME_DO_TIME`).
- Salva o arquivo de imagem diretamente na pasta `static/teams/<pais>/<api_id_antigo>.png` e copia para `staticfiles/`.

## Abordagem 2: SofaScore (Correção Manual)
Algumas vezes o TheSportsDB não tem o time ou a logo está feia/desatualizada (ex: escudo roxo do Flandria). Nesses casos, buscamos a logo correta no SofaScore.
Como o SofaScore bloqueia bots comuns, precisamos rodar um script na **MÁQUINA LOCAL (Localhost)** usando a biblioteca `curl_cffi`.

**Script:** `scripts/download_missing_specific_logos.py`
**Como usar:**
1. No seu localhost, identifique o ID correto do time no SofaScore (usando a URL do time ou pesquisando na API).
2. Adicione o time na função `main()` do script:
   ```python
   time_xyz = Team.objects.filter(name__iexact='NOME DO TIME').first()
   if not fix_team_logo(time_xyz, 'ID_DO_SOFASCORE'):
       print("Time não encontrado.")
   ```
3. Rode o script no seu ambiente Python local (que deve ter o pacote `curl-cffi` instalado):
   ```bash
   python scripts/download_missing_specific_logos.py
   ```
4. As imagens serão salvas na pasta `static/teams/<nome_do_pais>` (ex: `brasil`, `argentina`) com o prefixo `sofa_`. A função `fix_team_logo` já descobre o país automaticamente para evitar erros de digitação.
5. Faça o commit e push dos novos arquivos de imagem para o GitHub.

## Sincronizando com a Produção (Servidor VPS)
Depois que as imagens foram enviadas para o GitHub, o servidor de produção precisa saber que as imagens mudaram de ID e foram atualizadas.

1. Acesse o servidor via SSH e puxe as imagens:
   ```bash
   git pull origin main
   ```
2. Atualize as URLs no banco de dados via Shell do Django:
   ```bash
   python manage.py shell -c "from matches.models import Team; Team.objects.filter(name__iexact='NOME DO TIME').update(api_id='sofa_ID_DO_SOFASCORE')"
   ```
3. Copie as novas imagens para os arquivos estáticos expostos:
   ```bash
   python manage.py collectstatic --noinput
   ```
4. Limpe o cache do Django para as mudanças refletirem na página na mesma hora:
   ```bash
   python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('Cache limpo')"
   ```
