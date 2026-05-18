import subprocess
import os
import shutil

# Premier Liga (Rússia) usa o formato outono-primavera (XX/YY) - Identificado pelo ano de término
seasons = {
    2021: 29200,   # 20/21
    2022: 37038,   # 21/22
    2023: 42388,   # 22/23
    2024: 52470,   # 23/24
    2025: 61712,   # 24/25
    2026: 77142,   # 25/26
}

output_dir = "historical_data/Russia/PremierLiga"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Rússia (Premier Liga)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year-1}/{year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "203", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year-1}/{year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year-1}/{year}")

print("\n🎉 Todas as temporadas da Rússia foram baixadas com sucesso!")
