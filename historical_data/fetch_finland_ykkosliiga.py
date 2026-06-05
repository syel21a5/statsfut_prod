import subprocess
import os
import shutil

# Finland Ykkösliiga - Tournament 55
seasons = {
    2024: 58125,
    2025: 71183,
    2026: 88387,
}

output_dir = "historical_data/Finland/Ykkosliiga"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Finlândia Ykkösliiga...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["venv\\Scripts\\python", "proxy_sofascore_fetcher.py", "--tournament", "55", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as 3 temporadas da Finlândia Ykkösliiga foram baixadas com sucesso!")
