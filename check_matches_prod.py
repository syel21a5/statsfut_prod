import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, League

def check_ids():
    print("--- Verificando API IDs dos Jogos da Austrália ---")
    nj_team = Team.objects.get(name="Newcastle Jets FC", league_id=21)
    matches = Match.objects.filter(Q(home_team=nj_team) | Q(away_team=nj_team)).order_by('-date')
    
    print(f"Total de jogos do Newcastle: {matches.count()}")
    for m in matches:
        print(f"DB_ID: {m.id} | API_ID: {m.api_id} | {m.date} | {m.home_team.name} x {m.away_team.name} | Status: {m.status}")

if __name__ == '__main__':
    from django.db.models import Q
    check_ids()
