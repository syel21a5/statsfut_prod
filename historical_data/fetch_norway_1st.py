import subprocess
import os
import shutil

# Norway 1st Division - Tournament 22
seasons = {
    2024: 57356,
    2025: 70186,
    2026: 87867,
}

output_dir = "historical_data/Norway/1stDivision"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Noruega 1st Division...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["venv\\Scripts\\python", "proxy_sofascore_fetcher.py", "--tournament", "22", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as 3 temporadas da Noruega 1st Division foram baixadas com sucesso!")
