from matches.models import League, LeagueStanding, Season

league = League.objects.get(name='A League', country='Australia')
season = Season.objects.get(year=2026)
standings = LeagueStanding.objects.filter(league=league, season=season).order_by('position')

print(f"--- LISTA DE TIMES ({standings.count()}) ---")
for s in standings:
    print(f"ID: {s.team.id} | Nome: {s.team.name} | Pts: {s.points} | J: {s.played}")
