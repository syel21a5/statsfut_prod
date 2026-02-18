from collections import defaultdict
from datetime import timedelta
import json

from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import League, Team, Match, Season, LeagueStanding


class Command(BaseCommand):
    help = "Relatório de inventário do banco por País/Liga"

    def add_arguments(self, parser):
        parser.add_argument("--country", type=str)
        parser.add_argument("--league", type=str)
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **opts):
        FINISHED = ['Finished', 'FT', 'AET', 'PEN', 'FINISHED']
        SCHEDULED = ['Scheduled', 'Not Started', 'TIMED', 'UTC']
        now = timezone.now()
        future = now + timedelta(days=30)

        qs = League.objects.all()
        if opts.get("country"):
            qs = qs.filter(country__iexact=opts["country"])
        if opts.get("league"):
            qs = qs.filter(name__iexact=opts["league"])

        countries = defaultdict(list)
        for lg in qs.order_by("country", "name"):
            countries[lg.country].append(lg)

        data = []
        for country, leagues in countries.items():
            country_total = 0
            leagues_data = []
            for l in leagues:
                teams_count = Team.objects.filter(league=l).count()
                matches_qs = Match.objects.filter(league=l)
                m_total = matches_qs.count()
                m_finished = matches_qs.filter(status__in=FINISHED).count()
                m_scheduled = matches_qs.filter(status__in=SCHEDULED).count()
                m_upcoming_30 = matches_qs.filter(date__gte=now, date__lte=future, status__in=SCHEDULED).count()
                first_date = matches_qs.order_by("date").values_list("date", flat=True).first()
                last_date = matches_qs.order_by("-date").values_list("date", flat=True).first()
                seasons_from_matches = Season.objects.filter(matches__league=l).distinct().count()
                standings_count = LeagueStanding.objects.filter(league=l).count()
                seasons_from_standings = Season.objects.filter(standings__league=l).distinct().count()
                country_total += m_total

                leagues_data.append({
                    "league": l.name,
                    "country": l.country,
                    "teams": teams_count,
                    "matches": {
                        "total": m_total,
                        "finished": m_finished,
                        "scheduled": m_scheduled,
                        "upcoming_30d": m_upcoming_30,
                        "first_date": first_date.isoformat() if first_date else None,
                        "last_date": last_date.isoformat() if last_date else None,
                    },
                    "seasons": {
                        "from_matches": seasons_from_matches,
                        "standings_rows": standings_count,
                        "from_standings": seasons_from_standings,
                    },
                })
            data.append({
                "country": country,
                "total_matches": country_total,
                "leagues": leagues_data,
            })

        if opts.get("json"):
            self.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))
            return

        self.stdout.write("=== Database Inventory by Country / League ===")
        for entry in data:
            self.stdout.write(f"\n# {entry['country']}  (leagues: {len(entry['leagues'])})")
            for l in entry["leagues"]:
                first_s = l["matches"]["first_date"] or "-"
                last_s = l["matches"]["last_date"] or "-"
                self.stdout.write(
                    f"  - {l['league']}: teams={l['teams']}, "
                    f"matches={l['matches']['total']} [fin:{l['matches']['finished']} "
                    f"sched:{l['matches']['scheduled']} up30:{l['matches']['upcoming_30d']}] "
                    f"dates=({first_s} → {last_s}) "
                    f"seasons[matches]={l['seasons']['from_matches']} "
                    f"standings={l['seasons']['standings_rows']} "
                    f"seasons[stand]={l['seasons']['from_standings']}"
                )
