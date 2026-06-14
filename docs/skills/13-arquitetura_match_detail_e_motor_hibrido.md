# Arquitetura da Página Match Detail e Motor de Estatísticas Híbrido

## 1. Motor de Probabilidades Híbrido (`advanced_stats.py`)
O sistema agora utiliza um motor avançado, abandonando a dependência exclusiva de frequência histórica pura.

### Regra de Ouro (70/30)
Para mercados chave (Gols, BTTS, Combos de Dupla Chance), o motor aplica:
- **70% Peso Poisson:** Usa a força de ataque/defesa para calcular o xG (Expected Goals) e gera uma Matriz de Poisson Bidimensional para prever a probabilidade matemática exata dos placares.
- **30% Peso Histórico:** Frequência de ocorrência nos últimos jogos (para capturar o momento atual e a variância que a matemática pura não vê).

### Contexto de Jogo (Game State)
Para os mercados de **Cartões e Chutes ao Alvo**, a matemática pura não serve. Um time muito favorito chuta mais e sofre menos cartões. O motor aplica um multiplicador de **"Game State"** baseado na diferença do xG projetado entre os times. Se um time tem um xG muito maior, a média de escanteios e chutes dele sobe, e a média de cartões do adversário inflaciona.

### Limpeza de Mercados Obsoletos
- **Mercados Dinâmicos:** As barras de progresso agora calculam e exibem gols do Over 0.5 até o **Over 4.5**.
- **Remoções:** Mercados inúteis e não-oferecidos em casas de apostas (ex: *Over 26.5 Chutes*) foram sumariamente deletados do motor para poupar processamento.

---

## 2. Fair Odds (Odds Justas)
Em vez de mostrar apenas a probabilidade em porcentagem, implementamos o conceito de "Odd Justa" (True Odds). Isso ensina o usuário a buscar apostas de valor.

### Implementação
- **Template Filter (`matches_extras.py`):** Criamos um filtro customizado chamado `fair_odd`.
- **Fórmula:** `100 / probabilidade` (ex: 50% = Odd 2.00). O script protege contra divisão por zero, limitando o teto a "100.0".
- **Frontend:** O valor é injetado no HTML usando badges roxas modernas via `<span class="fair-odd-badge">Odd Justa: {{ prob|fair_odd }}</span>`. Aplicado nas barras de gols e no widget de Ambas Marcam (BTTS).

---

## 3. UI e Layout Elite (`match_detail.html`)
O design do painel abandonou o visual genérico e agora foca em uma interface "Premium/Elite".

### Regras de Ouro do Frontend
1. **Glassmorphism e CSS Grids:** Todo o layout é baseado em painéis de vidro (`.glass-panel`) flutuantes e grids flexíveis (`.grid-elite-2`, `.grid-elite-4`).
2. **Alinhamento Sagrado:** Há um cuidado obsessivo com o alinhamento de altura entre as colunas.
   - Na aba de "Gols", a coluna esquerda tem exatas 5 barras horizontais (`hbar-row`).
   - A coluna direita acomoda widgets com `d-flex flex-column gap-2`. Ajustes milimétricos no `padding`, redução de quebras de linha (`<br>`) indesejadas e um aumento leve do `gap` da coluna esquerda garantem que ambas terminem perfeitamente alinhadas no fundo.
3. **Limpeza de Poluição Visual:** Nenhum espaço inútil é permitido. Foi removida uma div com classe `ad-placeholder` que deixava um vão feio acima da aba de Especiais e Combos.

---

## 4. Internacionalização Estrita (i18n)
O StatsFut roda em 4 idiomas principais: Inglês (`en`), Português (`pt`), Espanhol (`es`) e Alemão (`de`).

### Regra de Ouro da Tradução
**NENHUMA PALAVRA HARDCODED!** Nenhuma string em português ou inglês pode ficar "jogada" no `match_detail.html`. Tudo deve ser "envelopado".

Exemplo correto:
`<span>Over 0.5 {% translate "Gols" %}</span>`

### Fluxo de Atualização de Idiomas
Quando uma nova palavra ou frase for adicionada à interface:
1. Adicione a palavra ao dicionário Python no script raiz `translate_po.py`. Certifique-se de adicionar a tradução nos quatro blocos de idioma (`en`, `de`, `es`, `pt`).
2. Execute o script `translate_po.py` no terminal. Ele irá varrer e atualizar automaticamente todos os arquivos `.po` nas pastas `locale/`.
3. Compile as mensagens usando o Docker (MUITO IMPORTANTE):
   `docker exec statsfut-web-1 python manage.py compilemessages -i venv`
4. Reinicie o contêiner se necessário:
   `docker restart statsfut-web-1`
