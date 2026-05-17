import subprocess
import os
import shutil

seasons = {
    2020: 23873,
    2021: 29186,
    2022: 36890,
    2023: 42256,
    2024: 52554,
    2025: 61666,
    2026: 77012
}

output_dir = "historical_data/Netherlands/Eredivisie"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Holanda (Eredivisie)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "37", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Holanda foram baixadas com sucesso!")
