import subprocess
import sys

LEAGUES = [
    'Premier League',
    'La Liga',
    'Bundesliga',
    'Serie A',
    'Ligue 1',
    'Primeira Liga',
    'Eredivisie',
    'Pro League',
    'Super Lig',
    'Super League'
]

print("--- Iniciando Limpeza e Recálculo de Tabelas ---")

# 1. Remover Duplicatas (Global)
print("\n>>> Removendo duplicatas de jogos (Global) <<<")
subprocess.run([sys.executable, "manage.py", "remove_match_duplicates"], check=True)

# 2. Recalcular Tabelas por Liga
# Nota: Normalização de times é mais específica para a Premier League no momento
for league in LEAGUES:
    print(f"\n>>> Processando Liga: {league} <<<")
    
    if league == 'Premier League':
        print(f"Normalizando times para {league}...")
        subprocess.run([sys.executable, "manage.py", "normalize_teams", "--league_name", league], check=True)

    print(f"Recalculando todas as temporadas para {league}...")
    
    cmd = [sys.executable, "manage.py", "recalculate_standings", "--league_name", league, "--season_year", "2026"]
    cmd_prev = [sys.executable, "manage.py", "recalculate_standings", "--league_name", league, "--season_year", "2025"]

    # Adiciona país para desambiguação
    if league == 'Premier League':
        cmd.extend(["--country", "Inglaterra"])
        cmd_prev.extend(["--country", "Inglaterra"])
    elif league == 'Super League':
        cmd.extend(["--country", "Grecia"]) # O importador usou G1 = Grécia. (China e Suíça foram seedados mas sem dados históricos csv)
        cmd_prev.extend(["--country", "Grecia"])
    elif league == 'Primeira Liga':
        cmd.extend(["--country", "Portugal"])
    elif league == 'Serie A':
        cmd.extend(["--country", "Italia"]) # Existe Serie A no Brasil no seed, mas importamos Italia
    elif league == 'Bundesliga':
        cmd.extend(["--country", "Alemanha"]) # Austria tb tem
    elif league == 'Ligue 1':
        cmd.extend(["--country", "Franca"])

    subprocess.run(cmd, check=False)
    subprocess.run(cmd_prev, check=False)

print("\n--- Processamento de Limpeza Concluído ---")
