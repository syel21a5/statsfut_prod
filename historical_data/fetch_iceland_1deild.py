import subprocess
import os
import shutil

# Iceland 1. deild - Tournament 675
seasons = {
    2024: 57386,
    2025: 70502,
    2026: 89207,
}

output_dir = "historical_data/Iceland/1deild"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Islândia 1. deild...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["venv\\Scripts\\python", "proxy_sofascore_fetcher.py", "--tournament", "675", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as 3 temporadas da Islândia 1. deild foram baixadas com sucesso!")
