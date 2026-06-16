import time
import subprocess
import schedule
from datetime import datetime
import sys
import os

# Garante que o output seja flushado para logs
sys.stdout.reconfigure(line_buffering=True)

def job_live():
    print(f"[{datetime.now()}] 🔴 Iniciando atualização de jogos AO VIVO...")
    try:
        # Busca apenas jogos ao vivo (leve e rápido)
        subprocess.run([sys.executable, "manage.py", "update_live_matches", "--mode", "live"], check=True)
        print(f"[{datetime.now()}] ✅ Jogos ao vivo atualizados.")
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] ❌ Erro na atualização ao vivo: {e}")

def job_recent():
    print(f"[{datetime.now()}] ⏪ Iniciando atualização de RESULTADOS RECENTES (Football-Data.org)...")
    try:
        # Busca resultados de ontem e hoje (cobre jogos finalizados que saíram do ao vivo)
        # Usa Football-Data.org (temos múltiplas chaves, sem custo de quota da Odds API)
        subprocess.run([sys.executable, "manage.py", "update_live_matches", "--mode", "recent", "--days", "1"], check=True)
        print(f"[{datetime.now()}] ✅ Resultados recentes atualizados.")
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] ❌ Erro na atualização de resultados recentes: {e}")

def job_upcoming():
    print(f"[{datetime.now()}] 📅 Iniciando atualização de PRÓXIMOS jogos (15 dias)...")
    try:
        # Busca próximos jogos (mais pesado, roda menos vezes)
        subprocess.run([sys.executable, "manage.py", "update_live_matches", "--mode", "upcoming"], check=True)
        print(f"[{datetime.now()}] ✅ Próximos jogos atualizados.")
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] ❌ Erro na atualização de próximos jogos: {e}")

def job_live_lay_bot():
    print(f"[{datetime.now()}] 🤖 Iniciando Live Lay Telegram Bot...")
    try:
        # Roda o bot de Lay (Usa APENAS O BANCO LOCAL, CUSTO ZERO DE API)
        subprocess.run([sys.executable, "manage.py", "run_live_lay_bot"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] ❌ Erro no Live Lay Bot: {e}")

# --- Configuração do Agendamento ---

# 1. Jogos AO VIVO: DESATIVADO no script local (Agora é controlado pelo Crontab inteligente para economizar API)
# schedule.every(1).minutes.do(job_live)

# 1.5. Live Lay Bot do Telegram: A cada 2 minutos (Custo zero, roda 100% local)
schedule.every(2).minutes.do(job_live_lay_bot)

# 2. Resultados Recentes (FALLBACK CARD BÁSICO): A cada 10 minutos
# Usa Football-Data.org (API Gratuita) para salvar o Radar quando a API principal falha!
schedule.every(10).minutes.do(job_recent)

# 3. Próximos Jogos: A cada 4 horas
schedule.every(4).hours.do(job_upcoming)

print("========================================================")
print("🚀 AGENDADOR DE FALLBACKS INICIADO (CUSTO ZERO API-FOOTBALL)")
print("========================================================")
print("Configuração:")
print("   - Ao Vivo API: DESATIVADO (Controlado pelo Crontab)")
print("   - Robô Telegram: a cada 2 minutos (Local)")
print("   - Fallback Card Básico (Recentes): a cada 10 minutos (API Gratuita)")
print("   - Próximos (15 dias): a cada 4 horas")
print("========================================================")
print("Pressione Ctrl+C para parar.")

# Executa uma vez imediatamente ao iniciar
job_recent()
job_upcoming()

while True:
    schedule.run_pending()
    time.sleep(1)
