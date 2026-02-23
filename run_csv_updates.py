import time
import subprocess
import schedule
import sys
from datetime import datetime

def job():
    print(f"[{datetime.now()}] Iniciando atualização diária via CSV (Football-Data.co.uk)...")
    try:
        # Lista de divisões para atualizar
        # (Divisão, Nome da Liga) - Deve bater com import_football_data.LEAGUE_MAPPING
        divisions = [
            ("E0", "Premier League"),
            ("SP1", "La Liga"),
            ("D1", "Bundesliga"),
            ("I1", "Serie A"),
            ("F1", "Ligue 1"),
            ("N1", "Eredivisie"),
            ("P1", "Primeira Liga"),
            ("BRA", "Brasileirao"),
            ("ARG", "Liga Profesional"),
            ("CZE", "First League"),
            ("T1", "Super Lig"),
            ("G1", "Super League"),
            ("AUT", "Bundesliga"),
            ("DNK", "Superliga"),
        ]

        # 1. Importa dados de todas as ligas
        print("1. Importando CSVs de todas as ligas...")
        for division, league_name in divisions:
            print(f"   -> Importando {league_name} ({division})...")
            subprocess.run([sys.executable, "manage.py", "import_football_data", "--division", division, "--min_year", "2026"], check=False)

        # 2. Resolve duplicatas de times (Global)
        # Usa o TEAM_NAME_MAPPINGS do utils.py para corrigir nomes
        print("2. Resolvendo duplicatas de times e ligas...")
        subprocess.run([sys.executable, "manage.py", "merge_duplicate_leagues"], check=False)
        # Hotfix específico para Premier League (Leeds, Newcastle, West Ham, Wolves)
        subprocess.run([sys.executable, "manage.py", "merge_pl_duplicates"], check=False)
        subprocess.run([sys.executable, "manage.py", "resolve_duplicate_teams"], check=False)
        
        # 3. Limpa duplicatas de jogos (Global)
        print("3. Limpando duplicatas de jogos...")
        subprocess.run([sys.executable, "manage.py", "remove_match_duplicates"], check=False)
        
        # 4. Recalcula tabelas de todas as ligas
        print("4. Recalculando tabelas...")
        for division, league_name in divisions:
            print(f"   -> Recalculando tabela: {league_name}...")
            subprocess.run([sys.executable, "manage.py", "recalculate_standings", "--league_name", league_name], check=False)
        
        print(f"[{datetime.now()}] Atualização diária concluída com sucesso.")
        
    except Exception as e:
        print(f"[{datetime.now()}] Erro crítico na atualização diária: {e}")

# Configuração do agendamento
# Roda a cada 4 horas
schedule.every(4).hours.do(job)

print("Iniciando agendador de atualizações CSV (A cada 4 horas)...")
# Executa uma vez imediatamente ao iniciar
job()

while True:
    schedule.run_pending()
    time.sleep(60) # Verifica a cada minuto
