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
**Observação para a IA:** Verifique se o projeto já usa `TIME_ZONE = 'UTC'`. Mantenha o padrão de código existente em `matches/scrapers/argentina/`.
