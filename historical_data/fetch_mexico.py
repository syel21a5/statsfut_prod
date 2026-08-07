import subprocess
import os
import shutil

# Liga MX Clausura (México)
# Identificado pelo ano de término (ex: Clausura 2026 -> 2026.json)
seasons = {
    2020: 26789,   # Clausura 2020
    2021: 35117,   # Clausura 2021
    2022: 40080,   # Clausura 2022
    2023: 47656,   # Clausura 2023
    2024: 57315,   # Clausura 2024
    2025: 70096,   # Clausura 2025
    2026: 87699,   # Clausura 2026
}

output_dir = "historical_data/Mexico/LigaMX"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica do México (Liga MX)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year-1}/{year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "11620", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year-1}/{year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year-1}/{year}")

print("\n🎉 Todas as temporadas do México foram baixadas com sucesso!")
