# Guia: Importação de Dados Históricos de Ligas no StatsFut

Este guia explica como buscar (fetch) e importar dados históricos de ligas de futebol do SofaScore para o banco de dados do **StatsFut** (local ou produção), utilizando o caso da **Escócia** como exemplo principal.

---

## 📋 Visão Geral do Processo

A importação histórica de uma liga é feita em duas etapas:
1. **Busca (Fetch) Local:** Executa-se um script local para baixar os JSONs das temporadas passadas da API do SofaScore (via proxy) e salvar na pasta `historical_data/[País]/[Liga]/`.
2. **Importação e Recalculo (Servidor/Local):** Executa-se um comando Django customizado (`python manage.py hist_[liga]`) para ler os JSONs, inserir os dados no banco de dados e recalcular as tabelas de classificação de cada ano.

---

## 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Caso Prático: Escócia (Premiership)

Se as tabelas da Escócia estão vazias no servidor, os arquivos JSON históricos das temporadas **2020 a 2025** já foram baixados e estão na pasta do projeto. Siga os passos abaixo:

### Passo 1: Atualizar o Código no Servidor VPS
Conecte-se via SSH ao seu servidor VPS, navegue até a pasta do projeto e garanta que você tem a versão mais recente do código e dos arquivos históricos:

```bash
cd /www/wwwroot/statsfut.com  # ou o diretório correspondente da sua VPS
git pull origin main
```

### Passo 2: Executar o Comando de Importação Histórica
Rode o comando específico de importação da Escócia usando o Python do ambiente virtual:

```bash
./venv/bin/python manage.py hist_scotland
```
*Este comando importará os anos de 2020, 2021, 2022, 2023, 2024 e 2025, recalculando a classificação de cada um automaticamente.*

### Passo 3: Limpeza de Duplicados e Cache
Para evitar times duplicados no banco e atualizar o cache das páginas do site, rode:

```bash
# Mesclar equipes duplicadas
./venv/bin/python manage.py merge_duplicate_teams

# Limpar o cache
./venv/bin/python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

---

## 🛠️ Caso Geral: Adicionando Histórico para Outra Liga

Caso precise fazer o processo completo para uma nova liga (por exemplo, França, Argentina, etc.):

### Passo 1: Obter os IDs das Temporadas no SofaScore
1. Acesse o SofaScore no navegador.
2. Navegue até a liga desejada e alterne os anos no seletor de temporadas.
3. Copie o ID da temporada na URL. Exemplo:
   * URL: `https://www.sofascore.com/tournament/football/scotland/premiership/36#id:77128`
   * **Tournament ID:** `36` (fixo para a liga)
   * **Season ID (2025):** `77128` (muda a cada ano)

### Passo 2: Criar o Script de Busca (Fetch) Local
Crie ou edite um arquivo de fetch dentro de `historical_data/`. Exemplo para a Escócia: `historical_data/fetch_scotland.py`:

```python
import subprocess
import os
import shutil

# Mapeamento Ano -> ID da Season no SofaScore
seasons = {
    2020: 28212,
    2021: 37029,
    2022: 41957,
    2023: 52588,
    2024: 62408,
    2025: 77128
}

output_dir = "historical_data/Escocia/Premiership"
os.makedirs(output_dir, exist_ok=True)

for year, season_id in seasons.items():
    # Executa o fetcher usando proxy para evitar bloqueios
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "36", "--season", str(season_id)]
    subprocess.run(cmd)

    # Salva o arquivo gerado
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    if os.path.exists(src):
        shutil.move(src, dst)
```

Rode o script localmente para gerar os arquivos JSON.

### Passo 3: Criar o Comando Django de Importação
Crie um arquivo em `matches/management/commands/hist_[nome_da_liga].py`. Use como modelo o arquivo `hist_scotland.py`:

```python
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League

class Command(BaseCommand):
    help = "Importa automaticamente payloads JSON históricos"

    def handle(self, *args, **options):
        base_dir = "historical_data/Escocia/Premiership"
        
        # Obtém ou cria a liga no banco
        league, created = League.objects.get_or_create(name='Premiership', country='Escocia')
        
        # Importa ano a ano
        for year in range(2020, 2026):
            filename = f"{base_dir}/{year}.json"
            if os.path.exists(filename):
                call_command('import_sofascore_payload', file=filename, league_id=league.id, season_year=year)
        
        # Recalcula tabelas
        for year in range(2020, 2026):
             call_command('recalculate_standings', league_name='Premiership', country='Escocia', season_year=year)
```

### Passo 4: Subir para o Git e Rodar na VPS
1. Adicione os arquivos gerados ao Git, faça o commit e dê push.
2. Na VPS, dê `git pull`.
3. Execute o comando criado:
   ```bash
   ./venv/bin/python manage.py hist_[nome_da_liga]
   ./venv/bin/python manage.py merge_duplicate_teams
   ./venv/bin/python manage.py shell -c "from django.core.cache import cache; cache.clear()"
   ```

---

## 🤖 Prompt Pronto para Enviar para outra IA

Se você estiver trabalhando com outra IA no futuro, copie e cole o texto abaixo:

```text
Olá! Estou trabalhando no projeto Django StatsFut. Preciso popular os dados históricos da liga da Escócia (Premiership) no servidor VPS de produção. 

Os arquivos JSON históricos (anos de 2020 a 2025) já foram baixados e estão salvos na pasta 'historical_data/Escocia/Premiership/' do repositório. O comando Django customizado de importação é 'hist_scotland'.

Por favor, me dê o passo a passo dos comandos para rodar no servidor VPS de produção para atualizar o repositório, rodar a importação desses arquivos, limpar possíveis times duplicados com o 'merge_duplicate_teams' e limpar o cache do Django.
```
