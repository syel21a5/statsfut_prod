import subprocess
import os
import shutil

# Sweden Superettan - Tournament 46
seasons = {
    2024: 57444,
    2025: 70171,
    2026: 87924,
}

output_dir = "historical_data/Sweden/Superettan"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Suécia Superettan...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["venv\\Scripts\\python", "proxy_sofascore_fetcher.py", "--tournament", "46", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as 3 temporadas da Suécia Superettan foram baixadas com sucesso!")
