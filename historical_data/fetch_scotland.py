import subprocess
import os
import shutil

seasons = {
    2020: 28212,
    2021: 37029,
    2022: 41957,
    2023: 52588,
    2024: 62408,
    2025: 77128
}

output_dir = "historical_data/Escocia/Premiership"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica de Escocia...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")

    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "36", "--season", str(season_id)]
    subprocess.run(cmd)

    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")

    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas de Escocia foram baixadas com sucesso!")
