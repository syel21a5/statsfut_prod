import time
import subprocess
import sys
import os
from datetime import datetime

# Configuração
INTERVALO_MINUTOS = 15  # Intervalo entre verificações (recomendado: 15 a 20 min para economizar créditos)
CMD = [sys.executable, "manage.py", "update_live_matches", "--mode=live"]

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base_dir)  # Garante que estamos na raiz do projeto
    
    log(f"Iniciando monitoramento de jogos ao vivo.")
    log(f"Intervalo configurado: {INTERVALO_MINUTOS} minutos.")
    log(f"Comando: {' '.join(CMD)}")
    
    while True:
        try:
            log("Executando verificação de jogos...")
            # Executa o comando e aguarda terminar
            result = subprocess.run(CMD, capture_output=True, text=True)
            
            # Mostra a saída do comando (para debug)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("ERROS:", result.stderr)
                
            log(f"Verificação concluída. Aguardando {INTERVALO_MINUTOS} minutos...")
            
        except Exception as e:
            log(f"ERRO CRÍTICO NO MONITOR: {e}")
        
        # Dorme pelo intervalo definido (em segundos)
        time.sleep(INTERVALO_MINUTOS * 60)

if __name__ == "__main__":
    main()
