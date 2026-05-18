import subprocess
import os
import shutil

# Ukrainian Premier League (Ucrânia) usa formato outono-primavera
# Mapeado pelo ano de término (ex: 20/21 -> 2021)
seasons = {
    2021: 29387,
    2022: 37040,
    2023: 45034,
    2024: 52774,
    2025: 62656,
    2026: 77625,
}

output_dir = "historical_data/Ukraine/PremierLeague"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Ucrânia (Premier League)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "218", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Ucrânia foram baixadas com sucesso!")
