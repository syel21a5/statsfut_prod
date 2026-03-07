import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match, LeagueStanding

# Verifying data for AU and AT
for country in ['Australia', 'Austria']:
    leagues = League.objects.filter(country=country)
    if not leagues.exists():
        print(f'No leagues found for {country}')
        continue
        
    for l in leagues:
        team_count = Team.objects.filter(league=l).count()
        match_count = Match.objects.filter(league=l).count()
        latest_standing = LeagueStanding.objects.filter(league=l).order_by('-points').first()
        
        print(f'League: {l.name} ({l.country})')
        print(f'  Teams: {team_count}')
        print(f'  Matches: {match_count}')
        print(f'  Standings found? {"Yes" if latest_standing else "No"}')
        
        # Check first team logo for this league
        t = Team.objects.filter(league=l).first()
        if t:
            from django.utils.text import slugify
            from matches.templatetags.team_tags import get_team_logo
            c_slug = slugify(l.country)
            l_slug = slugify(l.name)
            print(f'  Sample Team: {t.name} (API: {t.api_id})')
            print(f'  Expected Path: teams/{c_slug}/{l_slug}/{t.api_id}.png')
            print(f'  get_team_logo: {get_team_logo(t)}')
        else:
            print(f'  Warning: No teams found for {l.name}')
    print('-' * 20)
