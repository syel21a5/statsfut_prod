import subprocess
import os
import shutil

# Brasileirão Série B (Brasil) - Torneio 390
# Buscaremos as últimas 3 temporadas: 2024, 2025 e 2026 (ano civil)
seasons = {
    2024: 59015,
    2025: 72603,
    2026: 89840,
}

output_dir = "historical_data/Brasil/SerieB"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica do Brasileirão Série B (Brasil)...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "390", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as 3 temporadas do Brasileirão Série B foram baixadas com sucesso!")
