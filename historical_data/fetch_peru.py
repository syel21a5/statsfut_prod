import subprocess
import os
import shutil

seasons = {
    2020: 27096,
    2021: 35813,
    2022: 40118,
    2023: 48078,
    2024: 57741,
    2025: 70962,
    2026: 88529
}

output_dir = "historical_data/Peru/Liga1"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica do Peru...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "406", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas do Peru foram baixadas com sucesso!")
