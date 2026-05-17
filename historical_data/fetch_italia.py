import subprocess
import os
import shutil

seasons = {
    2020: 24644,
    2021: 32523,
    2022: 37475,
    2023: 42415,
    2024: 52760,
    2025: 63515,
    2026: 76457
}

output_dir = "historical_data/Italy/SerieA"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Itália (Serie A)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "23", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Itália foram baixadas com sucesso!")
