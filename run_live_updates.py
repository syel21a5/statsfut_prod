import time
import subprocess
import schedule
from datetime import datetime

def job():
    print(f"[{datetime.now()}] Iniciando atualização de jogos ao vivo e próximos...")
    try:
        # Executa o comando Django para atualizar jogos
        # --mode both busca tanto ao vivo quanto próximos 14 dias
        subprocess.run(["python3", "manage.py", "update_live_matches", "--mode", "both"], check=True)
        print(f"[{datetime.now()}] Atualização concluída com sucesso.")
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] Erro na atualização: {e}")

# Configuração do agendamento
# A cada 15 minutos para pegar gols e resultados rápidos
# Respeita limite de APIs: 
# API-Football: 200 req/dia. 15 min = 4 req/hora * 24 = 96 reqs (OK)
# Football-Data: 10 req/min. 1 req a cada 15 min é muito tranquilo.
schedule.every(15).minutes.do(job)

print("Iniciando agendador de atualizações ao vivo...")
print("Pressione Ctrl+C para parar.")

# Executa uma vez imediatamente ao iniciar
job()

while True:
    schedule.run_pending()
    time.sleep(1)
