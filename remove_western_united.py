from matches.models import Team, LeagueStanding
print("Removendo Western United (ID 2091)...")
Team.objects.filter(id=2091).delete()
LeagueStanding.objects.filter(team_id=2091).delete()
print("Western United removido com sucesso!")
