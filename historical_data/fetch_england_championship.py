import subprocess
import os
import shutil

# Championship (England 2nd Division)
seasons = {
    2020: 29438,
    2021: 37154,
    2022: 42401,
    2023: 52367,
    2024: 61961,
    2025: 77347,
}

output_dir = "historical_data/Inglaterra/Championship"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Championship (Inglaterra)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "18", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Championship foram baixadas com sucesso!")
