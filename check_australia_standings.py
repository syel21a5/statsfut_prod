import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, LeagueStanding, Match

def check():
    league = League.objects.get(id=21)
    
    print(f"--- Standings para {league.name} ---")
    standings = LeagueStanding.objects.filter(league=league).order_by('position')
    if not standings.exists():
        print("Nenhuma classificação encontrada!")
    for s in standings:
        print(f"{s.position}. {s.team.name} - Pts: {s.points} | J: {s.played} | V: {s.won} | E: {s.drawn} | D: {s.lost} | GP: {s.goals_for} | GC: {s.goals_against}")

    print(f"\n--- Últimos 5 Jogos no DB ---")
    matches = Match.objects.filter(league=league).order_by('-date')[:5]
    for m in matches:
        date = m.date.strftime('%Y-%m-%d') if m.date else 'Sem Data'
        print(f"{date} | {m.home_team.name} {m.home_score} x {m.away_score} {m.away_team.name} | Status: {m.status}")

if __name__ == '__main__':
    check()
