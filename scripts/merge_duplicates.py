import os
import django
import sys

# Adiciona o diretório atual ao path para encontrar o módulo 'core'
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, LeagueStanding, TeamGoalTiming, Goal
from django.db.models import Count

def find_duplicates():
    # Encontra nomes de times que se repetem na mesma liga
    duplicates = Team.objects.values('name', 'league').annotate(count=Count('id')).filter(count__gt=1)
    
    if not duplicates:
        print("Nenhum time duplicado encontrado localmente!")
        return

    for entry in duplicates:
        name = entry['name']
        league_id = entry['league']
        teams = Team.objects.filter(name=name, league_id=league_id).order_by('id')
        
        main_team = teams[0]
        other_teams = teams[1:]
        
        print(f"Mesclando {len(teams)} instâncias do time '{name}' (Liga ID: {league_id})")
        print(f"Manter ID: {main_team.id}, Remover IDs: {[t.id for t in other_teams]}")
        
        for duplicate in other_teams:
            # 1. Mover Partidas (Home e Away)
            Match.objects.filter(home_team=duplicate).update(home_team=main_team)
            Match.objects.filter(away_team=duplicate).update(away_team=main_team)
            
            # 2. Mover Gols
            Goal.objects.filter(team=duplicate).update(team=main_team)
            
            # 3. Mover Standings (com cuidado devido à UniqueConstraint existente)
            standings = LeagueStanding.objects.filter(team=duplicate)
            for s in standings:
                if not LeagueStanding.objects.filter(team=main_team, league=s.league, season=s.season).exists():
                    s.team = main_team
                    s.save()
                else:
                    s.delete() # Ja existe para o time principal
            
            # 4. Mover Goal Timings
            timings = TeamGoalTiming.objects.filter(team=duplicate)
            for t in timings:
                if not TeamGoalTiming.objects.filter(team=main_team, league=t.league, season=t.season).exists():
                    t.team = main_team
                    t.save()
                else:
                    t.delete()

            # 5. Deletar o duplicado
            duplicate.delete()
            print(f"Time ID {duplicate.id} removido.")

if __name__ == "__main__":
    find_duplicates()
