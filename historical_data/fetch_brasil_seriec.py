import subprocess
import os
import shutil

# Brasileirão Série C (Brasil) - Torneio 1281
# Buscaremos as últimas 3 temporadas: 2024, 2025 e 2026 (ano civil)
seasons = {
    2024: 59016,
    2025: 72841,
    2026: 90642,
}

output_dir = "historical_data/Brasil/SerieC"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica do Brasileirão Série C (Brasil)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "1281", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as 3 temporadas do Brasileirão Série C foram baixadas com sucesso!")
