import subprocess
import os
import shutil

# Major League Soccer (USA)
seasons = {
    2020: 26780,
    2021: 35964,
    2022: 40071,
    2023: 47955,
    2024: 57317,
    2025: 70158,
    2026: 86668,
}

output_dir = "historical_data/USA/MLS"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da MLS (Estados Unidos)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "242", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da MLS foram baixadas com sucesso!")
