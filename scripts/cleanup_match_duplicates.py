import os
import django
import sys
from django.db.models import Count
from datetime import timedelta

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, League

def cleanup_league_duplicates(league_name, country):
    print(f"--- Iniciando limpeza de duplicatas para {league_name} ({country}) ---")
    league = League.objects.filter(name__iexact=league_name, country__iexact=country).first()
    if not league and country.lower() in ['franca', 'frança', 'france']:
        for c in ['França', 'France', 'Franca']:
            league = League.objects.filter(name__iexact=league_name, country__iexact=c).first()
            if league: break
            
    if not league:
        print(f"Liga {league_name} ({country}) não encontrada.")
        return

    # Buscar jogos agrupados por times e data (ignorando a hora exata se necessário, mas aqui usaremos data cheia)
    # Primeiro, vamos identificar (home_team, away_team, date__date) que aparecem mais de uma vez
    duplicates = Match.objects.filter(league=league).values(
        'home_team', 'away_team', 'date__date'
    ).annotate(count=Count('id')).filter(count__gt=1)

    total_removed = 0
    for dup in duplicates:
        home_id = dup['home_team']
        away_id = dup['away_team']
        date_only = dup['date__date']
        
        # Buscar os matches reais desse grupo
        matches = Match.objects.filter(
            league=league,
            home_team_id=home_id,
            away_team_id=away_id,
            date__date=date_only
        ).order_by('-api_id', '-id') # Priorizar os que tem API ID (SofaScore começa com 'sofa_')
        
        if matches.count() > 1:
            keep = matches[0] # Manter o primeiro (mais provável de ser o do SofaScore por causa do 'sofa_')
            to_delete = matches[1:]
            
            print(f"Encontrados {len(matches)} para {keep.home_team} vs {keep.away_team} em {date_only}")
            print(f" Manter: ID {keep.id} (API: {keep.api_id})")
            
            for m in to_delete:
                print(f" Deletar: ID {m.id} (API: {m.api_id})")
                m.delete()
                total_removed += 1

    print(f"Total de duplicatas removidas: {total_removed}")

if __name__ == "__main__":
    # Limpar a França como prioridade
    cleanup_league_duplicates("Ligue 1", "Franca")
    # Opcional: Adicione outras ligas se houver suspeita
    # cleanup_league_duplicates("Bundesliga", "Austria")
    # cleanup_league_duplicates("A-League Men", "Australia")
