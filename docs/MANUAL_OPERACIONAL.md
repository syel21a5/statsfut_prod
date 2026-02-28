# Manual Operacional - Atualização de Ligas e Dados (StatsFut)

Este documento descreve o processo completo para manutenção, atualização e correção de dados das ligas no sistema StatsFut, considerando o cenário de **limite de requisições na API paga (The Odds API)** e a necessidade de validação em ambiente local (localhost) antes da publicação no servidor.

---

## 1. Visão Geral da Estratégia de Dados

Para economizar créditos da API paga, utilizamos uma estratégia híbrida:
1.  **Histórico e Passado (GRÁTIS):** Usamos "Scrapers" (robôs) que buscam dados do site *SoccerStats.com*. Isso não gasta créditos da API e é ideal para preencher temporadas passadas e corrigir resultados antigos.
2.  **Jogos Futuros e Ao Vivo (PAGO/LIMITADO):** Usamos a *The Odds API* apenas para buscar os próximos jogos (odds) e resultados muito recentes (últimos dias) para manter a classificação atualizada em tempo real.

---

## 2. Preparação do Ambiente (Localhost)

Antes de qualquer alteração no servidor, tudo deve ser testado no seu computador.

### Configuração das Chaves de API (`.env`)
No arquivo `.env` na raiz do projeto, você define as chaves da API para cada liga.
Exemplo:
```ini
ODDS_API_KEY_DENMARK_UPCOMING=sua_chave_aqui
ODDS_API_KEY_BRAZIL_UPCOMING=outra_chave_aqui
```
> **Nota:** Se a cota estourar, você pode criar uma nova conta na *The Odds API*, pegar uma nova chave e substituir aqui.

---

## 3. Passo a Passo: Adicionar ou Corrigir uma Liga

Vamos usar o exemplo da **Superliga da Dinamarca**, mas o processo é similar para outras.

### Passo 1: Atualizar Histórico (Sem gastar API)
Se faltam jogos antigos ou a tabela está errada com jogos duplicados, usamos o Scraper.

**Comando (no terminal do VS Code):**
```bash
python manage.py scrape_soccerstats_history --years 2026 --target_league Superliga
```
*   `--years 2026`: Busca a temporada atual (2025/2026). Use `2025` para a anterior, etc.
*   `--target_league`: Nome da liga conforme cadastrado no sistema (ex: `Superliga`, `Brasileirão`, `Premier League`).

**O que ele faz:**
*   Acessa o SoccerStats.
*   Baixa os resultados.
*   **Normaliza os nomes dos times** (ex: converte "Aarhus" para "AGF Aarhus" automaticamente) para evitar duplicatas.
*   Salva no banco de dados local.

### Passo 2: Buscar Jogos Futuros e Recentes (Gasta API)
Para ver os próximos jogos ("Upcoming") e atualizar resultados de hoje/ontem.

**Comando:**
```bash
python manage.py import_odds_api_fixtures --league soccer_denmark_superliga
```

**Se faltar um resultado específico de dias atrás (ex: jogo de segunda-feira):**
Use o parâmetro `--days` para olhar mais para trás no tempo.
```bash
python manage.py import_odds_api_fixtures --league soccer_denmark_superliga --scores --days 7
```
*   `--scores`: Diz para buscar resultados, não odds futuras.
*   `--days 7`: Busca nos últimos 7 dias (o padrão é 3).

### Passo 3: Recalcular a Tabela
Sempre que importar jogos novos, recalcule a classificação para garantir que os pontos estão certos.

**Comando:**
```bash
python manage.py recalculate_standings --league_name Superliga --country Dinamarca --season_year 2026
```

### Passo 4: Verificar se está tudo certo (Scripts de Checagem)
Criamos scripts específicos para validar os dados. Para a Dinamarca, temos o `final_denmark_check.py`.

**Comando:**
```bash
python final_denmark_check.py
```
**O que olhar:**
*   Se o número de jogos está correto (ex: 21 jogos por time).
*   Se não há duplicatas ("Duplicatas encontradas: 0").
*   Se não tem jogos em datas absurdas (ex: "Maio" no meio da temporada).

---

## 4. Enviando para o Servidor (Deploy)

Se funcionou no Localhost, hora de mandar para o ar.

1.  **Salvar alterações no Git:**
    ```bash
    git add .
    git commit -m "Correção e atualização da Superliga Dinamarca"
    git push
    ```

2.  **Acessar o Servidor:**
    (Via terminal SSH ou painel do servidor)

3.  **Baixar as atualizações:**
    ```bash
    cd /caminho/do/projeto/statsfut
    git pull
    ```

4.  **Aplicar Correções (Se necessário):**
    Se você criou um script de correção (como o `fix_denmark_server.py`), rode ele agora para limpar a sujeira antiga do servidor.
    ```bash
    python fix_denmark_server.py
    ```

5.  **Atualizar os Dados no Servidor:**
    Rode os mesmos comandos de importação que usou no local.
    ```bash
    # 1. Histórico (Grátis)
    python manage.py scrape_soccerstats_history --years 2026 --target_league Superliga

    # 2. Jogos Futuros/Recentes (API)
    python manage.py import_odds_api_fixtures --league soccer_denmark_superliga --scores --days 7
    
    # 3. Tabela
    python manage.py recalculate_standings --league_name Superliga --country Dinamarca --season_year 2026
    ```

---

## 5. Manutenção e Problemas Comuns

### Problema: Times Duplicados (ex: "Aarhus" e "AGF Aarhus")
Isso acontece quando o nome no site Scraper é diferente do nome na API.
**Solução:**
1.  Verifique o arquivo `matches/utils_odds_api.py`.
2.  Adicione o mapeamento correto no dicionário `ODDS_API_TEAM_MAPPINGS`.
    ```python
    "Nome Errado": "Nome Certo",
    "Aarhus": "AGF Aarhus",
    ```
3.  No servidor, rode o script de limpeza (ex: `fix_denmark_server.py`) ou crie um novo baseado nele se for outra liga.

### Problema: Cota da API Excedida
O sistema para de atualizar jogos futuros.
**Solução:**
1.  Crie uma nova conta grátis na *The Odds API*.
2.  Pegue a nova chave (`apikey`).
3.  Atualize o arquivo `.env` no servidor com a nova chave.
4.  Reinicie o serviço se necessário (geralmente não precisa para variáveis de ambiente lidas no script, mas é bom garantir).

### Problema: Jogos "Fantasmas" ou Datas Erradas
Às vezes o Scraper pega datas erradas (ex: ano seguinte).
**Solução:**
1.  Verifique o script `scrape_soccerstats_history.py`.
2.  Ajuste a lógica de ano (ex: se o mês for > 7, é o ano seguinte).
3.  Delete os jogos errados via banco de dados ou script de limpeza.

---

**Resumo dos Comandos Úteis:**

| Ação | Comando |
| :--- | :--- |
| **Baixar Histórico (Grátis)** | `python manage.py scrape_soccerstats_history --years 2026 --target_league [NomeLiga]` |
| **Baixar Odds/Futuros (Pago)** | `python manage.py import_odds_api_fixtures --league [LeagueKey]` |
| **Baixar Resultados Recentes** | `python manage.py import_odds_api_fixtures --league [LeagueKey] --scores --days 7` |
| **Recalcular Tabela** | `python manage.py recalculate_standings --league_name [NomeLiga] --country [Pais] --season_year 2026` |
| **Verificar Correção** | `python final_denmark_check.py` (ou script equivalente da liga) |
