import subprocess
import os
import shutil

seasons = {
    2020: 27042,
    2021: 35273,
    2022: 40230,
    2023: 48055,
    2024: 57353,
    2025: 69871,
    2026: 87931
}

output_dir = "historical_data/Japan/J1League"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica do Japão (J1 League)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    # Executa o fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "196", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Move payload.json gerado para a pasta histórica
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as temporadas do Japão foram baixadas com sucesso!")
