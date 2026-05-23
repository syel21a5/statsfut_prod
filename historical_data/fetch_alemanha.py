import subprocess
import os
import shutil

seasons = {
    2021: 28210,
    2022: 37166,
    2023: 42268,
    2024: 52608,
    2025: 63516,
    2026: 77333
}

output_dir = "historical_data/Germany/Bundesliga"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Alemanha (Bundesliga)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "35", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Alemanha foram baixadas com sucesso!")
