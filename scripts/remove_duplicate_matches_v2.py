import os
import django
import sys

# Adiciona o diretório atual ao path para encontrar o 'core'
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match
from django.db.models import Count

def remove_duplicate_matches():
    print("Iniciando limpeza de partidas duplicadas...")
    
    # Encontra partidas com o mesmo home_team, away_team e date
    duplicates = Match.objects.values('home_team', 'away_team', 'date').annotate(count=Count('id')).filter(count__gt=1)
    
    if not duplicates:
        print("Nenhuma partida duplicada encontrada!")
        return

    total_removed = 0
    for entry in duplicates:
        home_id = entry['home_team']
        away_id = entry['away_team']
        match_date = entry['date']
        
        # Pega todas as instâncias dessa partida
        matches = Match.objects.filter(
            home_team_id=home_id, 
            away_team_id=away_id, 
            date=match_date
        ).order_by('id')
        
        # Mantém a primeira (geralmente a que tem api_id se existir)
        # Se uma tiver api_id e a outra não, preferimos a com api_id
        main_match = matches.filter(api_id__isnull=False).first() or matches[0]
        others = matches.exclude(id=main_match.id)
        
        print(f"Limpando jogo: {main_match} em {match_date}")
        print(f"Removendo {others.count()} duplicatas.")
        
        removed_count, _ = others.delete()
        total_removed += removed_count

    print(f"Limpeza concluída! Total de partidas removidas: {total_removed}")

if __name__ == "__main__":
    remove_duplicate_matches()
