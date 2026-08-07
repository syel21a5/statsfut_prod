# Prompt padrão para integração de ligas secundárias (via Tor)

Sempre que quiser integrar uma liga secundária (2ª, 3ª ou 4ª divisão) ao StatsFut, basta copiar o texto abaixo, preencher os campos entre colchetes e me enviar no chat:

--- INÍCIO DO PROMPT ---

"Antigravity, vamos integrar a **[NOME DA LIGA, DIVISÃO E PAÍS]** ao sistema StatsFut como liga secundária (via Tor, sem GitHub Actions)!
Aqui está o link do SofaScore: **[LINK DO SOFASCORE AQUI]**

Por favor, execute o nosso pipeline padrão **'SofaScore Tor / Liga Secundária'** que já consolidamos:

1. **PESQUISA INICIAL**: Pesquise no código o Tournament ID e liste todos os Season IDs da API do SofaScore para os anos de 2020 até o ano atual dessa liga. Acesse também o nosso banco de dados local (Docker) para checar se a liga já existe cadastrada.
2. **CADASTRO DA LIGA**: Se a liga não existir no banco, crie-a via Django shell no Docker local com o nome, país e número da divisão corretos.
3. **SCRIPTS DE CARGA HISTÓRICA**: Crie o script de extração via Tor (`historical_data/fetch_[liga].py`) e o comando Django de importação (`matches/management/commands/hist_[liga].py`).
4. **EXTRAÇÃO LOCAL**: Execute o fetch das temporadas históricas usando o Tor local (porta 9150 no Windows) para baixar todos os JSONs.
5. **IMPORTAÇÃO E VALIDAÇÃO LOCAL**: Execute a importação no Docker local (`python manage.py hist_[liga]`), valide os times, partidas e o bloqueio de recálculo para tabelas complexas (playoffs).
6. **SEM CI/CD**: Essa liga **NÃO** será adicionada ao `master_fetcher.py` nem terá workflow do GitHub Actions. As atualizações futuras serão feitas via Tor diretamente na VPS.
7. **DEPLOY**: Se o teste local for um sucesso, faça o git commit e git push para a main (apenas dos scripts de carga e do comando Django, sem workflows).

--- FIM DO PROMPT ---
