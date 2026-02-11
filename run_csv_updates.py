import time
import subprocess
import schedule
from datetime import datetime

def job():
    print(f"[{datetime.now()}] Iniciando atualização diária via CSV (Football-Data.co.uk)...")
    try:
        # 1. Importa dados históricos e resultados recentes
        print("Importando CSVs...")
        subprocess.run(["python3", "manage.py", "import_football_data", "--min_year", "2026"], check=True)
        
        # 2. Normaliza times (caso venha nome novo)
        print("Normalizando times...")
        subprocess.run(["python3", "manage.py", "normalize_teams", "--league_name", "Premier League"], check=True)
        
        # 3. Limpa duplicatas
        print("Limpando duplicatas...")
        subprocess.run(["python3", "manage.py", "remove_match_duplicates"], check=True)
        
        # 4. Recalcula tabela
        print("Recalculando tabela...")
        subprocess.run(["python3", "manage.py", "recalculate_standings", "--league_name", "Premier League"], check=True)
        
        print(f"[{datetime.now()}] Atualização diária concluída.")
        
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] Erro na atualização diária: {e}")

# Configuração do agendamento
# Roda todo dia às 03:00 da manhã (horário do servidor)
# Football-Data.co.uk costuma atualizar de madrugada
schedule.every().day.at("03:00").do(job)

print("Iniciando agendador de atualizações CSV diárias (03:00)...")
# Não executa na inicialização, espera o horário agendado

while True:
    schedule.run_pending()
    time.sleep(60) # Verifica a cada minuto
