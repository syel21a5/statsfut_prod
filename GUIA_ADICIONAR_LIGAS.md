# Guia para Adicionar Novas Ligas (The Odds API)

Este documento serve como um guia técnico e prático para adicionar novas ligas ao sistema de atualização automática de jogos (futuros e ao vivo) utilizando a **The Odds API**.

Use este guia se você precisar configurar uma nova liga no futuro ou se quiser instruir outra IA a fazer isso por você.

---

## 1. Visão Geral do Sistema

O sistema foi projetado para economizar créditos e evitar bloqueios. Ele funciona da seguinte forma:

*   **Chaves Separadas:** Usamos chaves diferentes para jogos futuros (`UPCOMING`) e jogos ao vivo (`LIVE`).
*   **Múltiplas Chaves Ao Vivo:** Para jogos ao vivo, usamos até 3 chaves diferentes (`_LIVE_1`, `_LIVE_2`, `_LIVE_3`) que são escolhidas aleatoriamente para distribuir a carga.
*   **Smart Check:** O robô só gasta créditos da API se houver jogos daquela liga marcados para hoje ou acontecendo agora.

---

## 2. O Que Você Precisa Ter em Mãos

Antes de começar, você precisa dessas 3 informações:

1.  **Nome da Liga no Banco de Dados:** Exatamente como está cadastrado no seu site (ex: `Bundesliga`, `La Liga`, `Brasileirão Série B`).
2.  **Sport Key (Chave da API):** O código que a The Odds API usa para essa liga (ex: `soccer_germany_bundesliga`, `soccer_spain_la_liga`). Você encontra isso na documentação da The Odds API.
3.  **Chaves de API (API Keys):** O ideal é ter **4 chaves** novas para cada liga (1 para jogos futuros, 3 para ao vivo).

---

## 3. Passo a Passo Manual

Se você for fazer manualmente, siga estes 3 passos:

### Passo 1: Adicionar Chaves no `.env`
No arquivo `.env` (no servidor e local), adicione as chaves seguindo este padrão:

```env
# --- NOME DA NOVA LIGA ---
ODDS_API_KEY_NOVALIGA_UPCOMING=chave_aqui
ODDS_API_KEY_NOVALIGA_LIVE_1=chave_aqui
ODDS_API_KEY_NOVALIGA_LIVE_2=chave_aqui
ODDS_API_KEY_NOVALIGA_LIVE_3=chave_aqui
```

### Passo 2: Configurar Jogos Futuros (`import_odds_api_fixtures.py`)
Edite o arquivo `matches/management/commands/import_odds_api_fixtures.py`.
Adicione a nova liga no dicionário `LEAGUE_CONFIG` no início da classe:

```python
'soccer_novaliga_key': {
    'env_key': 'ODDS_API_KEY_NOVALIGA_UPCOMING',
    'db_name': 'Nome da Liga no DB',
    'country': 'País da Liga'
},
```

### Passo 3: Configurar Jogos Ao Vivo (`update_live_matches.py`)
Edite o arquivo `matches/management/commands/update_live_matches.py`.
Dentro do método `handle`, adicione a chamada para a nova liga:

```python
# Nova Liga
if self.should_check_live_league('Nome da Liga no DB', 'País'):
    fetch_live_odds_generic(
        league_name_db='Nome da Liga no DB',
        country_db='País',
        sport_key='soccer_novaliga_key',
        env_prefix='ODDS_API_KEY_NOVALIGA_LIVE', # Prefixo das chaves no .env
        label='Nome para Logs'
    )
```

---

## 4. Prompt Mestre (Para pedir para uma IA)

Se você estiver em outro computador e quiser pedir para uma IA (como ChatGPT, Claude, ou o próprio Trae/Cursor) fazer isso para você, copie e cole o texto abaixo, substituindo apenas as informações entre colchetes `[ ]`.

---
**COPIE AQUI:**

```text
Estou trabalhando no projeto StatsFut (Django). Preciso adicionar uma nova liga ao sistema de atualização da The Odds API.

Aqui estão as informações da nova liga:
- Nome no Banco de Dados: [NOME DA LIGA, ex: Bundesliga]
- País: [PAÍS, ex: Alemanha]
- Sport Key (The Odds API): [KEY DA API, ex: soccer_germany_bundesliga]

Aqui estão as novas chaves de API que eu criei para ela:
- Upcoming: [CHAVE_UPCOMING]
- Live 1: [CHAVE_LIVE_1]
- Live 2: [CHAVE_LIVE_2]
- Live 3: [CHAVE_LIVE_3]

Por favor, realize as seguintes alterações no código:

1. Adicione essas chaves no arquivo `.env` (com comentários organizados).
2. Adicione a configuração dessa liga no arquivo `matches/management/commands/import_odds_api_fixtures.py` (no dicionário LEAGUE_CONFIG).
3. Adicione a lógica de atualização ao vivo no arquivo `matches/management/commands/update_live_matches.py`, chamando a função `fetch_live_odds_generic` e usando o `should_check_live_league` para economizar créditos.

Mantenha o padrão de código existente e não apague as outras ligas.
```
---
