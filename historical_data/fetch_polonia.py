import subprocess
import os
import shutil

# Ekstraklasa usa formato de temporada XX/YY (outono-primavera)
# Salvamos pelo ano de início da temporada
seasons = {
    2020: 29222,   # 20/21
    2021: 37062,   # 21/22
    2022: 42004,   # 22/23
    2023: 52176,   # 23/24
    2024: 61236,   # 24/25
    2025: 76477,   # 25/26
}

output_dir = "historical_data/Poland/Ekstraklasa"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Polônia (Ekstraklasa)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year}/{year+1} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "202", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year}/{year+1} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}/{year+1}")

print("\n🎉 Todas as temporadas da Polônia foram baixadas com sucesso!")
