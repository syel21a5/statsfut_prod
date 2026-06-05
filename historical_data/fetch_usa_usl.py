import subprocess
import os
import shutil

# USA USL Championship - Torneio 13363
# Buscaremos as últimas 3 temporadas: 2024, 2025 e 2026 (ano civil)
seasons = {
    2024: 57319,
    2025: 70263,
    2026: 87611,
}

output_dir = "historical_data/USA/USL"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando a busca histórica da USL Championship...")

for year, season_id in seasons.items():
    print(f"\n--- Buscando Temporada {year} (SofaScore ID: {season_id}) ---")
    
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "13363", "--season", str(season_id), "--force-fallback"]
    subprocess.run(cmd)
    
    src = "payload.json"
    dst = os.path.join(output_dir, f"{year}.json")
    
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Temporada {year} salva com sucesso em {dst}")
    else:
        print(f"❌ Erro ao gerar payload para a temporada {year}")

print("\n🎉 Todas as 3 temporadas da USL Championship foram baixadas com sucesso!")
