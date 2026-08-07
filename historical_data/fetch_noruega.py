import subprocess
import os
import shutil

seasons = {
    2020: 26799,
    2021: 35403,
    2022: 40405,
    2023: 47806,
    2024: 57322,
    2025: 70174,
    2026: 87809
}

output_dir = "historical_data/Norway/Eliteserien"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Noruega (Eliteserien)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "20", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Noruega foram baixadas com sucesso!")
