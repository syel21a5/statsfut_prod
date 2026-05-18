import subprocess
import os
import shutil

# Allsvenskan (Suécia) usa formato de Ano Civil
seasons = {
    2021: 35306,
    2022: 40406,
    2023: 47730,
    2024: 57284,
    2025: 69956,
    2026: 87925,
}

output_dir = "historical_data/Sweden/Allsvenskan"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Suécia (Allsvenskan)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "40", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Suécia foram baixadas com sucesso!")
