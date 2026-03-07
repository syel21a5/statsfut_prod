import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, League

def check_australia_details():
    print("--- Verificação Técnica Austrália ---")
    try:
        league = League.objects.get(id=21)
        print(f"Liga: {league.name} (ID: {league.id})")
    except League.DoesNotExist:
        print("Erro: Liga 21 não encontrada!")
        return

    teams = Team.objects.filter(league=league)
    print(f"\nTotal de times encontrados: {teams.count()}")
    for t in teams:
        match_count = Match.objects.filter(models.Q(home_team=t) | models.Q(away_team=t)).count()
        print(f"ID: {t.id} | API_ID: {t.api_id} | Nome: {t.name} | Jogos no DB: {match_count}")

    last_matches = Match.objects.filter(league=league).order_by('-date')[:5]
    print("\nÚltimos 5 jogos registrados:")
    for m in last_matches:
        print(f"{m.date} | {m.home_team.name} {m.home_score} x {m.away_score} {m.away_team.name} | Status: {m.status}")

if __name__ == '__main__':
    from django.db import models
    check_australia_details()
