import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import LeagueStanding, Team, League

# Check leagues for Australia
for l in League.objects.filter(country='Australia'):
    print(f'League -> ID: {l.id}, Name: {l.name}, Country: {l.country}')

# Check team
t = Team.objects.filter(name__icontains='newcastle jets').first()
if t:
    print(f'Team: {t.name}, API ID: {t.api_id}, League: {t.league.name}')
    from django.utils.text import slugify
    country_slug = slugify(t.league.country)
    league_slug = slugify(t.league.name)
    print(f'Static path would be: teams/{country_slug}/{league_slug}/{t.api_id}.png')
    from matches.templatetags.team_tags import get_team_logo
    print(f'get_team_logo result: {get_team_logo(t)}')
