import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import LeagueStanding, Team
t = Team.objects.filter(name__icontains='newcastle jets').first()
s = LeagueStanding.objects.filter(team=t).exclude(league__name__icontains='Women').order_by('-points').first()
if s:
    print(f'Production DB -> Team: {s.team.name}, GP: {s.played}, Pts: {s.points}')
else:
    print('Not found')
