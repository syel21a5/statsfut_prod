import subprocess
import os
import shutil

seasons = {
    2020: 27395,
    2021: 36546,
    2022: 40536,
    2023: 48634,
    2024: 58264,
    2025: 71306,
    2026: 89288
}

output_dir = "historical_data/Uruguay/PrimeraDivision"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica do Uruguai...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "278", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move o payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas do Uruguai foram baixadas com sucesso!")
