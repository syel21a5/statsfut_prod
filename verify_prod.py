import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import LeagueStanding, Team, League

# Check leagues for Australia and Austria
for country in ['Australia', 'Austria']:
    for l in League.objects.filter(country=country):
        print(f'League -> ID: {l.id}, Name: {l.name}, Country: {l.country}')

# Check Australian team
t_au = Team.objects.filter(name__icontains='newcastle jets').first()
if t_au:
    print(f'Team (AU): {t_au.name}, API ID: {t_au.api_id}, League: {t_au.league.name}')
    from django.utils.text import slugify
    country_slug = slugify(t_au.league.country)
    league_slug = slugify(t_au.league.name)
    print(f'AU Static path: teams/{country_slug}/{league_slug}/{t_au.api_id}.png')
    from matches.templatetags.team_tags import get_team_logo
    print(f'AU get_team_logo result: {get_team_logo(t_au)}')

# Check Austrian team
t_at = Team.objects.filter(league__country='Austria').first()
if t_at:
    print(f'Team (AT): {t_at.name}, API ID: {t_at.api_id}, League: {t_at.league.name}')
    from django.utils.text import slugify
    country_slug = slugify(t_at.league.country)
    league_slug = slugify(t_at.league.name)
    print(f'AT Static path: teams/{country_slug}/{league_slug}/{t_at.api_id}.png')
    from matches.templatetags.team_tags import get_team_logo
    print(f'AT get_team_logo result: {get_team_logo(t_at)}')
