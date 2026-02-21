# Master Prompt para Criação de Scrapers de Novas Ligas

**Objetivo:** Criar um sistema de raspagem (scraper) para obter **Jogos Futuros (Fixtures)** e **Resultados Recentes (Results)** de uma nova liga no site **SoccerStats**, contornando limitações de API.

**Contexto Técnico:**
O projeto é em **Django**. O site SoccerStats exibe horários em fuso europeu/UTC, mas precisamos salvar no banco de dados respeitando o `TIME_ZONE = 'UTC'` do Django e ajustando para a visualização correta (ex: subtrair 3h para Américas se necessário, ou converter corretamente).

---

## Copie e cole o texto abaixo para a IA:

Estou adicionando uma nova liga ao meu projeto Django (StatsFut) e preciso criar scrapers para ela, similar ao que foi feito para a "Liga Profesional" da Argentina. Por favor, siga estes passos:

### 1. Preparação
- **Site Alvo:** `https://www.soccerstats.com/latest.asp?league=NOME_DA_LIGA` (Eu vou te passar o link exato).
- **Bibliotecas:** Use `requests` e `BeautifulSoup`.
- **Setup Django:** O script deve ser "standalone", ou seja, precisa configurar o `django.setup()` e importar os modelos (`League`, `Season`, `Team`, `Match`) no início.

### 2. Script de Jogos Futuros (`scrape_fixtures.py`)
Crie um script que:
- Acesse a tabela de "Next Matches" ou "Fixtures" do SoccerStats.
- **Importante (Timezone):** O SoccerStats geralmente mostra horários da Europa. Se a liga for da América (ex: Brasil, Argentina), precisamos converter esse horário.
    - *Lógica:* Ler o horário do site -> Tratar como UTC -> Subtrair o fuso (ex: -3h) se necessário para bater com o horário local real -> Salvar no banco.
- **Mapeamento de Times:** Crie uma função `_resolve_team(name)` que tenta buscar o time no banco.
    - Se não achar exato, use um dicionário `mappings = {'Nome Site': 'Nome Banco'}` que eu vou preencher com os nomes corretos.
- **Ação:** Salvar com `status='Scheduled'` e atualizar a data se o jogo já existir.

### 3. Script de Resultados (`scrape_results.py`)
Crie um segundo script que:
- Acesse a tabela de "Latest Results" do mesmo link.
- Busque o placar (ex: "2 - 1").
- Encontre a partida correspondente no banco de dados (buscando por times e data aproximada, margem de +/- 2 dias).
- **Ação:** Atualizar `home_team_score`, `away_team_score` e mudar `status='Finished'`.

### 4. Automação (Cron)
- Gere o comando para adicionar esses scripts no `crontab` do Linux.
- Fixtures: Rodar a cada 6 horas (`0 */6 * * *`).
- Results: Rodar a cada 2 horas (`0 */2 * * *`).

### 5. Dados da Nova Liga
- **Nome da Liga no Banco:** [INSERIR NOME AQUI]
- **País:** [INSERIR PAÍS AQUI]
- **URL do SoccerStats:** [INSERIR URL AQUI]

---

## Template detalhado para scrapers baseados no Brasileirão (SoccerStats)

Quando quiser criar um scraper similar ao do Brasileirão para outra liga (usando o comando `scrape_soccerstats_brazil.py` como modelo), você pode usar o prompt abaixo diretamente em qualquer IA. Basta preencher os campos marcados com `<<<...>>>`.

> CONTEXTO DO PROJETO  
> - Projeto Django chamado **StatsFut**.  
> - Modelos principais em `matches/models.py`:
>   - `League(name, country)`
>   - `Season(year)` (ano de término da temporada, ex: 2026 para 2025/26)
>   - `Team(name, league, api_id)`
>   - `Match(league, season, home_team, away_team, date, status, home_score, away_score, ...)`
> - O projeto usa `TIME_ZONE = 'UTC'` e salva horários em UTC no banco. A conversão para o fuso do usuário é feita no front-end.
>
> ---
>
> LIGA QUE QUERO ADICIONAR (PREENCHER AQUI):
> - Nome da liga no banco (`League.name`): `<<<NOME_DA_LIGA_NO_DB>>>`
> - País (`League.country`): `<<<PAIS>>>`
> - Ano da temporada (`Season.year`): `<<<ANO_TEMPORADA>>>`
> - URL principal do SoccerStats (latest/fixtures): `<<<URL_SOCCERSTATS>>>`
> - Timezone local dos jogos (para conversão UTC): `<<<TIMEZONE_DA_LIGA>>>` (ex: `America/Sao_Paulo`, `Europe/Madrid`)
>
> ---
>
> O QUE A IA DEVE FAZER
>
> 1. Criar um **management command** em:
>    - `matches/management/commands/scrape_soccerstats_<<<slug_liga>>>.py`
>    - Ele deve seguir o padrão de `scrape_soccerstats_brazil.py`:
>      - Usar `requests` + `BeautifulSoup`.
>      - Buscar a tabela de “Matches” ou “Next matches” da URL `<<<URL_SOCCERSTATS>>>`.
>      - Ler as linhas na estrutura:
>        - `td[0]`: data (ex: `"Tue 24 Feb"`)
>        - `td[1]`: times (ex: `"Time A<br>Time B"`)
>        - `td[2]`: placar ou status (ex: `"2-1"`, `"pp."`)
>
> 2. Datas e horários:
>    - Parsear dia e mês com base em `<<<ANO_TEMPORADA>>>`.
>    - Ler o horário se existir.
>    - Assumir que o horário está no fuso `<<<TIMEZONE_DA_LIGA>>>`.
>    - Converter para UTC (usando `pytz` ou `zoneinfo`) e salvar em `Match.date` como datetime aware.
>
> 3. Times:
>    - Garantir que `League(name=<<<NOME_DA_LIGA_NO_DB>>>, country=<<<PAIS>>>)` exista (criar se necessário).
>    - Garantir que `Season(year=<<<ANO_TEMPORADA>>>)` exista.
>    - Criar uma função `resolve_team(name, league)`:
>      - Usar um dicionário de mapeamento `mapping = {"Nome no SoccerStats": "Nome no Banco"}`.
>      - Tentar:
>        - busca exata `name__iexact`,
>        - depois `name__icontains`.
>      - Se não encontrar, logar um aviso sem quebrar o comando.
>
> 4. Status do jogo:
>    - A partir da coluna de status/placar:
>      - Se contiver `"pp"` ou `"postp"` → `status = "Postponed"` e opcionalmente `date = None` para não entrar em próximos jogos.
>      - Se tiver placar `"X-Y"` ou `"X - Y"`:
>        - extrair `home_score` e `away_score`,
>        - `status = "Finished"`.
>      - Caso contrário → `status = "Scheduled"` ou `"Not Started"`.
>
> 5. Salvar no banco evitando duplicatas:
>    - Usar `Match.objects.update_or_create` com chave:
>      - `league`, `season`, `home_team`, `away_team`.
>    - Em caso de `MultipleObjectsReturned`:
>      - Selecionar todas as partidas com esse filtro.
>      - Escolher uma como canônica (ex: menor `id`).
>      - Atualizar essa canônica com `date`, `status`, `home_score`, `away_score`.
>      - Deletar as duplicatas.
>      - Logar quantas entradas foram mescladas.
>
> 6. Integração com limpeza de dados:
>    - Se necessário, criar um comando `cleanup_<<<slug_liga>>>_bad_teams.py` em `matches/management/commands/`:
>      - Mapa de nomes ruins → nomes bons.
>      - Remoção de times lixo (ex: `"MATCHES"`).
>      - Tratar erros envolvendo `matches_teamgoaltiming` ou `LeagueStanding` com `try/except` e `DELETE` raw, seguindo o padrão de `cleanup_brazil_bad_teams.py`.
>    - No final do scraper, chamar:
>      - `call_command("cleanup_<<<slug_liga>>>_bad_teams")` se esse comando existir.
>
> 7. Cron (automação):
>    - Sugerir uma linha de cron no estilo:
>
>      ```bash
>      0 */4 * * * cd /www/wwwroot/statsfut.com && source /www/wwwroot/statsfut.com/venv/bin/activate && python manage.py scrape_soccerstats_<<<slug_liga>>> >> /www/wwwroot/statsfut.com/logs/cron_<<<slug_liga>>>_soccerstats.log 2>&1
>      ```
>
>    - Assim, a liga será atualizada automaticamente sem intervenção manual.
>
> 8. Estilo e segurança:
>    - Não adicionar comentários desnecessários.
>    - Seguir o padrão de código de `scrape_soccerstats_brazil.py` e dos scrapers de Argentina.
>    - Não expor chaves de API nem segredos.

---
**Observação para a IA:** Verifique se o projeto já usa `TIME_ZONE = 'UTC'`. Mantenha o padrão de código existente em `matches/scrapers/argentina/` e em `matches/management/commands/scrape_soccerstats_brazil.py`.
