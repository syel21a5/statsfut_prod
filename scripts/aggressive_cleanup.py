import os
import django
import sys
from datetime import datetime

# Adiciona o diretório atual ao path para encontrar o 'core'
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, LeagueStanding

def cleanup_and_reset():
    print("Iniciando limpeza agressiva de partidas e reset de classificação...")
    
    all_matches = Match.objects.all().order_by('home_team', 'away_team', 'date')
    seen = {} # (home, away, date_only) -> match_id
    to_delete = []
    
    for m in all_matches:
        if m.date:
            day = m.date.date()
            key = (m.home_team_id, m.away_team_id, day)
            
            if key in seen:
                # Já vimos esse jogo hoje!
                # Preferimos manter o que tem api_id
                existing_id = seen[key]
                existing_match = Match.objects.get(id=existing_id)
                
                if not existing_match.api_id and m.api_id:
                    to_delete.append(existing_id)
                    seen[key] = m.id
                else:
                    to_delete.append(m.id)
            else:
                seen[key] = m.id

    if to_delete:
        print(f"Removendo {len(to_delete)} partidas duplicadas (ignorando hora)...")
        Match.objects.filter(id__in=to_delete).delete()
    else:
        print("Nenhuma duplicata de data aproximada encontrada.")

    # Reset de Standings para forçar o sistema a recalcular
    print("Limpando tabela de classificação (LeagueStanding) para forçar recálculo...")
    LeagueStanding.objects.all().delete()
    
    print("\nSUCESSO! Agora você pode rodar o GitHub Action do Sofascore.")
    print("O sistema irá recriar a classificação do zero com os dados limpos.")

if __name__ == "__main__":
    cleanup_and_reset()
