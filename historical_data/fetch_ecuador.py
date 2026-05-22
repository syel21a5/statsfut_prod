import subprocess
import os
import shutil

seasons = {
    2020: 26952,
    2021: 35552,
    2022: 40503,
    2023: 48720,
    2024: 58043,
    2025: 71184,
    2026: 89674
}

output_dir = "historical_data/Ecuador/LigaPro"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica do Equador...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "240", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas do Equador foram baixadas com sucesso!")