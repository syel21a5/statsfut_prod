import os
import sys
from collections import defaultdict
from datetime import timedelta

import django
from django.utils import timezone

# Setup Django environment using current repo path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import League, Team, Match, Season, LeagueStanding
from matches.utils import COUNTRY_REVERSE_TRANSLATIONS

FINISHED_STATUSES = ['Finished', 'FT', 'AET', 'PEN', 'FINISHED']
SCHEDULED_STATUSES = ['Scheduled', 'Not Started', 'TIMED', 'UTC']

print("=== Database Inventory by Country / League ===")

countries = defaultdict(list)
for lg in League.objects.all().order_by("country", "name"):
    countries[lg.country].append(lg)

now = timezone.now()
future = now + timedelta(days=30)

for country, leagues in countries.items():
    print(f"\n# {country}  (leagues: {len(leagues)})")
    total_matches_country = 0
    for l in leagues:
        teams_count = Team.objects.filter(league=l).count()
        matches_qs = Match.objects.filter(league=l)
        m_total = matches_qs.count()
        m_finished = matches_qs.filter(status__in=FINISHED_STATUSES).count()
        m_scheduled = matches_qs.filter(status__in=SCHEDULED_STATUSES).count()
        m_upcoming_30 = matches_qs.filter(date__gte=now, date__lte=future, status__in=SCHEDULED_STATUSES).count()
        first_date = matches_qs.order_by("date").values_list("date", flat=True).first()
        last_date = matches_qs.order_by("-date").values_list("date", flat=True).first()
        seasons_from_matches = Season.objects.filter(matches__league=l).distinct().count()
        standings_count = LeagueStanding.objects.filter(league=l).count()
        seasons_from_standings = Season.objects.filter(standings__league=l).distinct().count()
        total_matches_country += m_total

        first_s = first_date.strftime("%Y-%m-%d") if first_date else "-"
        last_s = last_date.strftime("%Y-%m-%d") if last_date else "-"
        print(f"  - {l.name}: teams={teams_count}, matches={m_total} [fin:{m_finished} sched:{m_scheduled} up30:{m_upcoming_30}] "
              f"dates=({first_s} → {last_s}) seasons[matches]={seasons_from_matches} standings={standings_count} seasons[stand]={seasons_from_standings}")

    print(f"  Total matches in {country}: {total_matches_country}")

print("\n=== Country Slug Test ===")
for slug in ["england","spain","brazil","belgium","czech republic"]:
    db_country = COUNTRY_REVERSE_TRANSLATIONS.get(slug)
    exists = League.objects.filter(country__iexact=db_country or slug).exists()
    print(f"  slug='{slug}' -> country='{db_country or slug}', exists={exists}")
