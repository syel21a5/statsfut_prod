from datetime import datetime
from typing import Optional

import pandas as pd
import pytz
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import League, Match, Season, Team


class Command(BaseCommand):
    help = "Importa First League (República Tcheca) a partir do worldfootball.net (all_matches)"

    def add_arguments(self, parser):
        parser.add_argument("--season", type=int, required=True, help="Ano de término da temporada, ex: 2026")
        parser.add_argument("--dry_run", action="store_true")

    def handle(self, *args, **options):
        season_year: int = options["season"]
        dry_run: bool = options["dry_run"]

        season_code = f"{season_year-1}-{str(season_year)[-2:]}"
        url = f"https://www.worldfootball.net/all_matches/cze-1-liga-{season_code}/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        }
        self.stdout.write(self.style.SUCCESS(f"Baixando: {url}"))
        r = requests.get(url, headers=headers, timeout=25)
        if r.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Falha ao acessar {url}: {r.status_code}"))
            return

        league, _ = League.objects.get_or_create(name="First League", country="Republica Tcheca")
        season_obj, _ = Season.objects.get_or_create(year=season_year)

        try:
            tables = pd.read_html(r.text)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"read_html falhou: {e}"))
            return

        target = None
        for t in tables:
            cols = [str(c).strip().lower() for c in t.columns.tolist()]
            if "result" in cols and len(cols) >= 4:
                target = t
                break
        if target is None:
            self.stdout.write(self.style.ERROR("Nenhuma tabela compatível com coluna 'Result' encontrada."))
            return

        mapping = {
            "Slavia Praha": "Slavia Prague",
            "Sparta Praha": "Sparta Prague",
            "Slovan Liberec": "Slovan Liberec",
            "Jablonec": "Jablonec",
            "Viktoria Plzen": "Viktoria Plzen",
            "Plzen": "Viktoria Plzen",
            "Karviná": "Karvina",
            "Karvina": "Karvina",
            "Hradec Králové": "Hradec Kralove",
            "Hradec Kralove": "Hradec Kralove",
            "Sigma Olomouc": "Sigma Olomouc",
            "Zlín": "Zlin",
            "Zlin": "Zlin",
            "Teplice": "Teplice",
            "Pardubice": "Pardubice",
            "Bohemians 1905": "Bohemians",
            "Baník Ostrava": "Banik Ostrava",
            "Banik Ostrava": "Banik Ostrava",
            "Mladá Boleslav": "Mlada Boleslav",
            "Mlada Boleslav": "Mlada Boleslav",
            "Slovácko": "Slovacko",
            "Slovacko": "Slovacko",
            "Dukla Praha": "Dukla Praha",
            "Dukla Prague": "Dukla Praha",
        }

        def norm_team(name: str) -> str:
            name = (name or "").strip()
            return mapping.get(name, name)

        def parse_date(val: str) -> Optional[datetime]:
            if not val:
                return None
            candidates = [
                "%d/%m/%Y",
                "%d.%m.%Y",
                "%Y-%m-%d",
                "%d/%m/%y",
                "%d.%m.%y",
            ]
            for fmt in candidates:
                try:
                    dt = datetime.strptime(val.strip(), fmt)
                    return timezone.make_aware(dt, pytz.UTC)
                except Exception:
                    continue
            return None

        count = 0
        cols = [str(c).strip() for c in target.columns.tolist()]
        date_idx = None
        home_idx = None
        away_idx = None
        res_idx = None
        for i, c in enumerate(cols):
            lc = c.lower()
            if res_idx is None and "result" in lc:
                res_idx = i
            if home_idx is None and ("home" in lc or "team 1" in lc or "home team" in lc):
                home_idx = i
            if away_idx is None and ("away" in lc or "team 2" in lc or "guest team" in lc):
                away_idx = i
            if date_idx is None and "date" in lc:
                date_idx = i
        if res_idx is None or home_idx is None or away_idx is None:
            self.stdout.write(self.style.ERROR("Não foi possível identificar colunas (home/away/result)."))
            return

        for _, row in target.iterrows():
            vals = [str(x).strip() for x in row.values.tolist()]
            try:
                home = norm_team(vals[home_idx])
                away = norm_team(vals[away_idx])
                if not home or not away or home == "nan" or away == "nan":
                    continue
                result = vals[res_idx]
                if not result or result.lower() in {"-", "postponed", "abandoned"}:
                    continue
                main_result = result.split()[0].replace("–", ":").replace("-", ":")
                if ":" not in main_result:
                    continue
                hg_str, ag_str = main_result.split(":")[:2]
                hg = int(hg_str)
                ag = int(ag_str)
                dt_aware = None
                if date_idx is not None:
                    dt_aware = parse_date(vals[date_idx])

                if not dry_run:
                    home_team, _ = Team.objects.get_or_create(name=home, league=league)
                    away_team, _ = Team.objects.get_or_create(name=away, league=league)
                    if home_team == away_team:
                        continue
                    defaults = {"home_score": hg, "away_score": ag, "status": "Finished"}
                    if dt_aware:
                        defaults["date"] = dt_aware
                    Match.objects.update_or_create(
                        league=league,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        defaults=defaults,
                    )
                count += 1
            except Exception:
                continue

        self.stdout.write(self.style.SUCCESS(f"Partidas processadas: {count}"))
        if count == 0:
            self.stdout.write(self.style.WARNING("Nenhuma partida encontrada – verifique se a página mudou ou se o season informado está correto."))
