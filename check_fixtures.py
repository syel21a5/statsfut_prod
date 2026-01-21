
import os
import django
import sys
from datetime import datetime

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import Match, League

# Check for scheduled matches
upcoming = Match.objects.filter(status='Scheduled', date__gte=datetime.now()).count()
total_matches = Match.objects.count()
leagues = League.objects.all()

print(f"Total Matches in DB: {total_matches}")
print(f"Upcoming 'Scheduled' Matches: {upcoming}")
print(f"Leagues: {[l.name for l in leagues]}")

# List a few if they exist
if upcoming > 0:
    for m in Match.objects.filter(status='Scheduled', date__gte=datetime.now()).order_by('date')[:5]:
        print(f"{m.date}: {m.home_team} vs {m.away_team}")
else:
    print("No upcoming matches found. We likely need to scrape fixtures.")
