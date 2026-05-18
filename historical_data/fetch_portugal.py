import subprocess
import os
import shutil

# Primeira Liga (Portugal) usa o formato outono-primavera (XX/YY)
seasons = {
    2020: 32456,   # 20/21
    2021: 37358,   # 21/22
    2022: 42655,   # 22/23
    2023: 52769,   # 23/24
    2024: 63670,   # 24/25
    2025: 77806,   # 25/26
}

output_dir = "historical_data/Portugal/PrimeiraLiga"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica de Portugal (Primeira Liga)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year}/{year+1} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "238", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year}/{year+1} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}/{year+1}")

print("\n🎉 Todas as temporadas de Portugal foram baixadas com sucesso!")
