import os
import django
import sys

# Adiciona o diretório atual ao path para encontrar o 'core'
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, LeagueStanding, TeamGoalTiming, Goal

def merge_bragantino():
    print("Iniciando mesclagem manual do Bragantino...")
    
    try:
        # Tenta encontrar os dois times
        # No servidor, um está como 'Red Bull Bragantino' e outro como 'Bragantino'
        target_team = Team.objects.filter(name__icontains="Red Bull Bragantino").first()
        source_team = Team.objects.filter(name="Bragantino").first()

        if not target_team or not source_team:
            print(f"Erro: Não encontramos um dos times. Target: {target_team}, Source: {source_team}")
            # Tenta busca reversa se falhar
            if not target_team: target_team = Team.objects.filter(name="Bragantino").first()
            if not source_team: source_team = Team.objects.filter(name__icontains="Red Bull").first()

        if target_team and source_team and target_team.id != source_team.id:
            print(f"Mesclando '{source_team.name}' (ID {source_team.id}) para '{target_team.name}' (ID {target_team.id})")
            
            # 1. Partidas
            Match.objects.filter(home_team=source_team).update(home_team=target_team)
            Match.objects.filter(away_team=source_team).update(away_team=target_team)
            
            # 2. Gols
            Goal.objects.filter(team=source_team).update(team=target_team)
            
            # 3. Standings
            for s in LeagueStanding.objects.filter(team=source_team):
                if not LeagueStanding.objects.filter(team=target_team, league=s.league, season=s.season).exists():
                    s.team = target_team
                    s.save()
                else:
                    s.delete()
            
            # 4. Timings
            for t in TeamGoalTiming.objects.filter(team=source_team):
                if not TeamGoalTiming.objects.filter(team=target_team, league=t.league, season=t.season).exists():
                    t.team = target_team
                    t.save()
                else:
                    t.delete()
            
            # 5. Deletar
            source_team.delete()
            print("Sucesso! Bragantino unificado.")
        else:
            print("Os times não foram encontrados ou já são o mesmo.")

    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    merge_bragantino()
