import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, LeagueStanding, TeamGoalTiming, Goal

def merge_teams(source_name, target_name):
    # Encontra o time criado acidentalmente (Source)
    # E o time verdadeiro que queremos manter (Target)
    source_team = Team.objects.filter(name__icontains=source_name).first()
    target_team = Team.objects.filter(name=target_name).first()
    
    if source_team and target_team and source_team.id != target_team.id:
        print(f"Mesclando '{source_team.name}' (ID {source_team.id}) -> '{target_team.name}' (ID {target_team.id})")
        
        # Move or delete matches where source is home
        for m in Match.objects.filter(home_team=source_team):
            if Match.objects.filter(home_team=target_team, away_team=m.away_team, date=m.date).exists():
                m.delete() # Duplicate fixture, delete
            else:
                m.home_team = target_team
                m.save()
                
        # Move or delete matches where source is away
        for m in Match.objects.filter(away_team=source_team):
            if Match.objects.filter(home_team=m.home_team, away_team=target_team, date=m.date).exists():
                m.delete() # Duplicate fixture, delete
            else:
                m.away_team = target_team
                m.save()
        Goal.objects.filter(team=source_team).update(team=target_team)
        
        # Delete source standings/timings to avoid constraint conflicts (they will be recalculated anyway)
        LeagueStanding.objects.filter(team=source_team).delete()
        TeamGoalTiming.objects.filter(team=source_team).delete()
        
        source_team.delete()
        print("Sucesso!")
    else:
        print(f"Nenhuma mesclagem necessária para '{source_name}'.")

def clean_all_brazil():
    print("Limpando times criados pelo Sofascore...")
    merge_teams("Atlético Mineiro", "Atletico-MG")
    merge_teams("Vasco da Gama", "Vasco")
    merge_teams("Red Bull Bragantino", "Bragantino")
    print("Concluído!")

if __name__ == "__main__":
    clean_all_brazil()
