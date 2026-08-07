import subprocess
import os
import shutil

seasons = {
    2020: 24108,
    2021: 32553,
    2022: 37707,
    2023: 44513,
    2024: 53223,
    2025: 64052,
    2026: 78175
}

output_dir = "historical_data/Greece/SuperLeague"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Grécia...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "185", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Grécia foram baixadas com sucesso!")
