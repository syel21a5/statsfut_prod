import os
import django
import sys

# Adicionar o diretório atual ao path para encontrar o módulo 'betstats'
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import LeagueStanding, Season, Team

print(f"Total de Temporadas: {Season.objects.count()}")
for season in Season.objects.all().order_by('-year'):
    count = LeagueStanding.objects.filter(season=season).count()
    champion = LeagueStanding.objects.filter(season=season, position=1).first()
    print(f"Temporada {season.year}: {count} times na tabela. Campeão: {champion.team.name if champion else 'N/A'} ({champion.points if champion else 0} pts)")

print("\nExemplo de Tabela 2024 (Top 5):")
standings = LeagueStanding.objects.filter(season__year=2024, position__lte=5).order_by('position')
for s in standings:
    print(f"{s.position}. {s.team.name} - {s.points} pts (GP: {s.played}, W: {s.won})")
