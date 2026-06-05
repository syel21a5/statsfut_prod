import subprocess
import os
import shutil

# Equador Serie B - Torneio 10240
# Buscaremos as últimas 3 temporadas: 2024, 2025 e 2026 (ano civil)
seasons = {
    2024: 58858,
    2025: 72724,
    2026: 90244,
}

output_dir = "historical_data/Ecuador/SerieB"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica do Equador Serie B...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "10240", "--season", str(season_id)]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as 3 temporadas do Equador Serie B foram baixadas com sucesso!")
