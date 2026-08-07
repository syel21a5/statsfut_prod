import subprocess
import os
import shutil

seasons = {
    2020: 26940,
    2021: 35615,
    2022: 40342,
    2023: 48157,
    2024: 57370,
    2025: 70501,
    2026: 89094
}

output_dir = "historical_data/Iceland/BestaDeildKarla"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Islândia...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "188", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Islândia foram baixadas com sucesso!")