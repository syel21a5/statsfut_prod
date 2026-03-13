import os
import subprocess
import time

seasons = {
    "2016": "11429",
    "2017": "13100",
    "2018": "16183",
    "2019": "22931",
    "2020": "27591",
    "2021": "36166",
    "2022": "40557",
    "2023": "48982",
    "2024": "58766",
    "2025": "72034"
}

python_exe = os.path.join("venv", "Scripts", "python.exe")
tournament_id = "325"

for year, season_id in seasons.items():
    print(f"\n===== Processando Temporada {year} (ID: {season_id}) =====")
    
    # 1. Fetch data
    print(f"Buscando dados no SofaScore...")
    fetch_cmd = [python_exe, "proxy_sofascore_fetcher.py", "--tournament", tournament_id, "--season", season_id]
    subprocess.run(fetch_cmd, check=True)
    
    # 2. Import data
    print(f"Importando para o banco de dados...")
    import_cmd = [python_exe, "manage.py", "import_sofascore_payload", "--league_name", "Brasileirao", "--country", "Brasil", "--season_year", year]
    subprocess.run(import_cmd, check=True)
    
    # 3. Recalculate standings
    print(f"Recalculando classificação...")
    recalc_cmd = [python_exe, "manage.py", "recalculate_standings", "--league_name", "Brasileirao", "--country", "Brasil", "--season_year", year]
    subprocess.run(recalc_cmd, check=True)
    
    print(f"Temporada {year} concluída!")
    time.sleep(2) # Respiro entre temporadas
