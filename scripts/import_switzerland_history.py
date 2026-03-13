import os
import subprocess
import time

seasons = {
    "2016": "10385",
    "2017": "11741",
    "2018": "13426",
    "2019": "17465",
    "2020": "23982",
    "2021": "32512",
    "2022": "37158",
    "2023": "42276",
    "2024": "52366",
    "2025": "61658",
    "2026": "77152",
}

def import_all():
    python_exe = r"i:\GitHub\statsfut\statsfut\venv\Scripts\python.exe"
    
    for year, season_id in seasons.items():
        print(f"\n[{year}] Importando Temporada SofaScore ID: {season_id}...")
        
        # 1. Fetch Payload
        fetch_cmd = [python_exe, "proxy_sofascore_fetcher.py", "--tournament", "215", "--season", season_id]
        subprocess.run(fetch_cmd, check=True)
        
        # 2. Import Matches
        import_cmd = [python_exe, "manage.py", "import_sofascore_payload", "--file", "payload.json", "--league_id", "42", "--season_year", year]
        subprocess.run(import_cmd, check=True)
        
        print(f"[{year}] Concluído!")
        time.sleep(2)

if __name__ == "__main__":
    import_all()
