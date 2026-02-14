import subprocess
import sys
import os

# Setup Django environment if needed (though we are calling manage.py subprocess)
# List of divisions to import
# E0 = Premier League
# SP1 = La Liga
# I1 = Serie A
# D1 = Bundesliga
# F1 = Ligue 1
# P1 = Primeira Liga
# N1 = Eredivisie
# B1 = Pro League
# T1 = Super Lig
# G1 = Super League (Greece)

DIVISIONS = ['E0', 'SP1', 'I1', 'D1', 'F1', 'P1', 'N1', 'B1', 'T1', 'G1']
MIN_YEAR = 2010

print(f"--- Iniciando Importação em Lote (2010-2026) ---")
print(f"Ligas: {DIVISIONS}")

for div in DIVISIONS:
    print(f"\n>>> Importando Divisão: {div} <<<")
    try:
        subprocess.run(
            [sys.executable, "manage.py", "import_football_data", "--division", div, "--min_year", str(MIN_YEAR)], 
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Erro ao importar {div}: {e}")

print("\n--- Importação em Lote Concluída ---")
print("Nota: O Brasil não está incluído pois o football-data.co.uk não fornece dados históricos detalhados para o Brasileirão.")
