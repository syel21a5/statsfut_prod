import subprocess
import os
import shutil

seasons = {
    2021: 32501,
    2022: 37223,
    2023: 42409,
    2024: 52376,
    2025: 61643,
    2026: 77559
}

output_dir = "historical_data/Spain/LaLiga"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da Espanha (La Liga)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "8", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas da Espanha foram baixadas com sucesso!")
