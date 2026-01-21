import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, League, Season
from django.db.models import Count

print('=== RESUMO DOS DADOS ===\n')

print('LIGAS:')
for league in League.objects.all():
    print(f'  - {league.name} ({league.country})')

print(f'\nTOTAL DE PARTIDAS: {Match.objects.count()}')

print('\nPARTIDAS POR LIGA:')
for league in League.objects.annotate(num_matches=Count('matches')).order_by('-num_matches'):
    print(f'  {league.name}: {league.num_matches} jogos')

print('\nPARTIDAS POR TEMPORADA:')
for season in Season.objects.annotate(num_matches=Count('matches')).order_by('year'):
    print(f'  {season} ({season.year}): {season.num_matches} jogos')
