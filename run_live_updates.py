import os
import time
import subprocess
import django
from django.utils import timezone
from datetime import timedelta

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match

def run_update():
    now = timezone.now()
    # Buffer: verificar se tem jogo nos próximos 30 minutos ou já em andamento
    buffer_time = now + timedelta(minutes=30)
    
    live_or_soon = Match.objects.filter(
        date__lte=buffer_time,
        status__in=['Scheduled', 'Live']
    ).exclude(status='Finished')

    if not live_or_soon.exists():
        # Mas pelo menos uma vez a cada 6 horas vamos buscar novos fixtures 
        # (Isso seria melhor em outro script, mas vamos manter simples por enquanto)
        print(f"[{time.strftime('%H:%M:%S')}] Sem jogos ativos. Scan lento (60s)...")
        time.sleep(60) # Dorme mais se não tem nada rolando para economizar
        return



    print(f"[{time.strftime('%H:%M:%S')}] Atualizando jogos ao vivo...")
    try:
        subprocess.run(["python", "manage.py", "update_live_matches", "--mode", "live"], check=True)
    except Exception as e:
        print(f"Erro na atualização: {e}")


if __name__ == "__main__":
    print("Iniciando monitoramento em tempo real (Modo Turbo: Refresh a cada 15s)")
    while True:
        try:
            run_update()
            # Como temos 8 chaves, podemos rodar tranquilamente a cada 15 segundos
            # 4 update/min * 60 min = 240 requests/hora.
            # Com 8 chaves (1000/dia cada = 8000), temos sobra para rodar 24h se precisar.
            time.sleep(15) 
        except KeyboardInterrupt:
            print("Monitoramento paralisado.")
            break
        except Exception as e:
            print(f"Erro fatal no loop: {e}")
            time.sleep(60)
