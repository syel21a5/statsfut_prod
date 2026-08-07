import os
import subprocess
import time

seasons = {
    "2016": "10335",
    "2017": "11829",
    "2018": "13375",
    "2019": "17343",
    "2020": "24097",
    "2021": "28216",
    "2022": "36894",
    "2023": "42404",
    "2024": "52383",
    "2025": "61459",
    "2026": "77040"
}

python_exe = os.path.join("venv", "Scripts", "python.exe")
tournament_id = "38"

for year, season_id in seasons.items():
    print(f"\n===== Processando Temporada {year} (ID: {season_id}) =====")
    
    # 1. Fetch data
    print(f"Buscando dados no SofaScore...")
    fetch_cmd = [python_exe, "proxy_sofascore_fetcher.py", "--tournament", tournament_id, "--season", season_id]
    subprocess.run(fetch_cmd, check=True)
    
    # 2. Import data
    print(f"Importando para o banco de dados...")
    import_cmd = [python_exe, "manage.py", "import_sofascore_payload", "--league_name", "Pro League", "--country", "Belgica", "--season_year", year]
    subprocess.run(import_cmd, check=True)
    
    # 3. Recalculate standings
    print(f"Recalculando classificação...")
    recalc_cmd = [python_exe, "manage.py", "recalculate_standings", "--league_name", "Pro League", "--country", "Belgica", "--season_year", year]
    subprocess.run(recalc_cmd, check=True)
    
    print(f"Temporada {year} concluída!")
    time.sleep(1)
