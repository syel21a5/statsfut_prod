import re
from datetime import datetime, date, time as dtime

import pytz
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import League, Match, Season, Team


class Command(BaseCommand):
    help = "Importa histórico da First League (República Tcheca) usando dados openfootball/europe"

    def add_arguments(self, parser):
        parser.add_argument("--min_season", type=int, default=2010)
        parser.add_argument("--max_season", type=int, default=None)
        parser.add_argument("--dry_run", action="store_true")

    def handle(self, *args, **options):
        min_season = options["min_season"]
        max_season = options["max_season"] or timezone.now().year
        dry_run = options["dry_run"]

        league, _ = League.objects.get_or_create(
            name="First League", country="Republica Tcheca"
        )

        total_matches = 0
        for season_year in range(min_season, max_season + 1):
            start_year = season_year - 1
            end_suffix = str(season_year)[-2:]
            season_dir = f"{start_year}-{end_suffix}"
            url = f"https://raw.githubusercontent.com/openfootball/europe/master/czech-republic/{season_dir}/cz.1.txt"

            try:
                resp = requests.get(url, timeout=20)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Erro ao buscar {url}: {e}")
                )
                continue

            if resp.status_code != 200:
                self.stdout.write(
                    self.style.WARNING(
                        f"Ignorando temporada {season_year}: status {resp.status_code}"
                    )
                )
                continue

            season_obj, _ = Season.objects.get_or_create(year=season_year)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processando First League {season_year} a partir de {url}"
                )
            )
            count = self._process_file(
                resp.text, league, season_obj, season_year, dry_run
            )
            total_matches += count
            self.stdout.write(
                self.style.SUCCESS(
                    f"Temporada {season_year}: {count} partidas processadas"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"Total de partidas processadas: {total_matches}")
        )

    def _process_file(self, text, league, season_obj, season_year, dry_run):
        lines = text.splitlines()
        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }

        current_date = None
        count = 0

        time_and_match_re = re.compile(
            r"^(?:(?P<time>\d{1,2}[:.]\d{2})\s+)?(?P<home>.+?)\s+(?P<hg>\d+)\s*-\s*(?P<ag>\d+)\s+(?P<away>[^@]+?)(?:\s+@.*)?$"
        )

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            if line.startswith("="):
                continue
            if "Round" in line or "Matchday" in line:
                continue

            if line.startswith("[") and "]" in line:
                inner = line[1 : line.index("]")]
                parts = inner.split()
                day = None
                month = None
                for part in parts:
                    if "/" in part:
                        try:
                            m_str, d_str = part.split("/")
                            m_key = m_str[:3].lower()
                            month = month_map.get(m_key)
                            day = int(d_str)
                        except Exception:
                            month = None
                            day = None
                if month and day:
                    year_for_date = season_year - 1 if month >= 7 else season_year
                    try:
                        current_date = date(year_for_date, month, day)
                    except ValueError:
                        current_date = None
                continue

            m = time_and_match_re.match(line)
            if not m:
                continue
            if current_date is None:
                continue

            home_name = m.group("home").strip()
            away_name = m.group("away").strip()
            try:
                hg = int(m.group("hg"))
                ag = int(m.group("ag"))
            except Exception:
                continue

            if not home_name or not away_name:
                continue

            home_team, _ = Team.objects.get_or_create(name=home_name, league=league)
            away_team, _ = Team.objects.get_or_create(name=away_name, league=league)

            if home_team == away_team:
                continue

            time_str = m.group("time")
            if time_str and ":" in time_str:
                try:
                    hour, minute = map(int, time_str.replace(".", ":").split(":"))
                except Exception:
                    hour, minute = 0, 0
            else:
                hour, minute = 0, 0

            naive_dt = datetime.combine(current_date, dtime(hour, minute))
            match_date = timezone.make_aware(naive_dt, pytz.UTC)

            if dry_run:
                count += 1
                continue

            defaults = {
                "home_score": hg,
                "away_score": ag,
                "status": "Finished",
                "date": match_date,
            }

            Match.objects.update_or_create(
                league=league,
                season=season_obj,
                home_team=home_team,
                away_team=away_team,
                defaults=defaults,
            )
            count += 1

        return count

