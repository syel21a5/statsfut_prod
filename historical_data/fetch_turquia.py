import subprocess
import os
import shutil

# Trendyol Süper Lig (Turquia) usa formato outono-primavera
# Mapeado pelo ano de término (ex: 20/21 -> 2021)
seasons = {
    2021: 29506,
    2022: 37466,
    2023: 42632,
    2024: 53190,
    2025: 63814,
    2026: 77805,
}

output_dir = "historical_data/Turkey/SuperLig"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Turquia (Süper Lig)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "52", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Turquia foram baixadas com sucesso!")
