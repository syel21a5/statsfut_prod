import os
import csv
from datetime import datetime
from io import StringIO

import pytz
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import League, Team, Match, Season


class Command(BaseCommand):
    help = "Importa dados históricos da football-data.co.uk para o banco"

    def add_arguments(self, parser):
        parser.add_argument(
            "--root",
            type=str,
            help="Diretório onde estão os CSVs baixados da football-data.co.uk",
        )
        parser.add_argument(
            "--division",
            type=str,
            default="E0",
            help="Código da divisão na football-data (padrão: E0 = Premier League)",
        )
        parser.add_argument(
            "--min_year",
            type=int,
            default=2016,
            help="Ano mínimo da temporada (ano de término) para importar",
        )

    def handle(self, *args, **options):
        root = options.get("root")
        division = options["division"]
        min_year = options["min_year"]

        league, _ = League.objects.get_or_create(
            name="Premier League", country="Inglaterra"
        )

        total_files = 0
        total_rows = 0
        created_matches = 0
        updated_matches = 0

        use_files = (
            root
            and os.path.isdir(root)
            and any(fname.lower().endswith(".csv") for fname in os.listdir(root))
        )

        if use_files:
            for fname in os.listdir(root):
                if not fname.lower().endswith(".csv"):
                    continue
                path = os.path.join(root, fname)
                total_files += 1
                self.stdout.write(self.style.SUCCESS(f"Processando arquivo: {fname}"))
                with open(path, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    r, c, u = self._process_reader(
                        reader, division, min_year, league
                    )
                    total_rows += r
                    created_matches += c
                    updated_matches += u
        else:
            current_year = timezone.now().year
            end_year = current_year + 1
            for season_year in range(min_year, end_year + 1):
                url, code = self._build_url(season_year, division)
                try:
                    resp = requests.get(url, timeout=15)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Erro ao buscar {url}: {e}"))
                    continue
                if resp.status_code != 200 or "404" in resp.text[:100]:
                    continue
                total_files += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Processando temporada {season_year}: {url}")
                )
                if root and os.path.isdir(root):
                    fname = f"{division}_{code}.csv"
                    path = os.path.join(root, fname)
                    try:
                        with open(path, "w", encoding="utf-8", newline="") as f:
                            f.write(resp.text)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Erro ao salvar {path}: {e}"))
                reader = csv.DictReader(StringIO(resp.text))
                r, c, u = self._process_reader(reader, division, min_year, league)
                total_rows += r
                created_matches += c
                updated_matches += u

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Importação concluída"))
        self.stdout.write(f"Arquivos CSV processados: {total_files}")
        self.stdout.write(f"Linhas lidas: {total_rows}")
        self.stdout.write(f"Jogos criados: {created_matches}")
        self.stdout.write(f"Jogos atualizados: {updated_matches}")

    def _process_reader(self, reader, division, min_year, league):
        rows = 0
        created = 0
        updated = 0
        for row in reader:
            rows += 1
            div = row.get("Div")
            if div != division:
                continue

            date_str = row.get("Date") or row.get("DATE")
            if not date_str:
                continue
            match_date = self._parse_date(date_str)
            if not match_date:
                continue

            season_year = self._season_year_from_date(match_date)
            if season_year < min_year:
                continue

            season, _ = Season.objects.get_or_create(year=season_year)

            home_name = row.get("HomeTeam") or row.get("Home")
            away_name = row.get("AwayTeam") or row.get("Away")
            if not home_name or not away_name:
                continue

            home_team, _ = Team.objects.get_or_create(name=home_name, league=league)
            away_team, _ = Team.objects.get_or_create(name=away_name, league=league)

            match_date_aware = match_date
            if timezone.is_naive(match_date_aware):
                match_date_aware = timezone.make_aware(match_date_aware, pytz.UTC)

            fthg = self._to_int(row.get("FTHG"))
            ftag = self._to_int(row.get("FTAG"))
            hthg = self._to_int(row.get("HTHG"))
            htag = self._to_int(row.get("HTAG"))

            hs = self._to_int(row.get("HS"))
            ast = self._to_int(row.get("AS"))
            hst = self._to_int(row.get("HST"))
            ast_on = self._to_int(row.get("AST"))
            hf = self._to_int(row.get("HF"))
            af = self._to_int(row.get("AF"))
            hc = self._to_int(row.get("HC"))
            ac = self._to_int(row.get("AC"))
            hy = self._to_int(row.get("HY"))
            ay = self._to_int(row.get("AY"))
            hr = self._to_int(row.get("HR"))
            ar = self._to_int(row.get("AR"))

            defaults = {
                "date": match_date_aware,
            }

            if fthg is not None:
                defaults["home_score"] = fthg
            if ftag is not None:
                defaults["away_score"] = ftag
            if hthg is not None:
                defaults["ht_home_score"] = hthg
            if htag is not None:
                defaults["ht_away_score"] = htag

            if hs is not None:
                defaults["home_shots"] = hs
            if ast is not None:
                defaults["away_shots"] = ast
            if hst is not None:
                defaults["home_shots_on_target"] = hst
            if ast_on is not None:
                defaults["away_shots_on_target"] = ast_on
            if hf is not None:
                defaults["home_fouls"] = hf
            if af is not None:
                defaults["away_fouls"] = af
            if hc is not None:
                defaults["home_corners"] = hc
            if ac is not None:
                defaults["away_corners"] = ac
            if hy is not None:
                defaults["home_yellow"] = hy
            if ay is not None:
                defaults["away_yellow"] = ay
            if hr is not None:
                defaults["home_red"] = hr
            if ar is not None:
                defaults["away_red"] = ar

            match, created_flag = Match.objects.update_or_create(
                league=league,
                season=season,
                home_team=home_team,
                away_team=away_team,
                date=match_date_aware,
                defaults=defaults,
            )

            if created_flag:
                created += 1
            else:
                updated += 1

        return rows, created, updated

    def _parse_date(self, value):
        value = value.strip()
        for fmt in ("%d/%m/%y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    def _season_year_from_date(self, dt):
        year = dt.year
        if dt.month >= 8:
            return year + 1
        return year

    def _build_url(self, season_year, division):
        prev = (season_year - 1) % 100
        cur = season_year % 100
        code = f"{prev:02d}{cur:02d}"
        return f"https://www.football-data.co.uk/mmz4281/{code}/{division}.csv", code

    def _to_int(self, value):
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None
