import subprocess
import os
import shutil

seasons = {
    2020: 26853,
    2021: 35356,
    2022: 40096,
    2023: 47643,
    2024: 57264,
    2025: 69799,
    2026: 87238
}

output_dir = "historical_data/Paraguay/PrimeraDivision"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica do Paraguai...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "11540", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas do Paraguai foram baixadas com sucesso!")
