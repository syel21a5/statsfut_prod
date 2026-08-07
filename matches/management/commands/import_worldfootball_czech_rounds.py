from datetime import datetime
from typing import Optional

import pandas as pd
import pytz
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import League, Match, Season, Team


class Command(BaseCommand):
    help = "Importa todos os jogos da First League (República Tcheca) por rodadas no worldfootball.net"

    def add_arguments(self, parser):
        parser.add_argument("--season", type=int, required=True, help="Ano de término da temporada, ex: 2026")
        parser.add_argument("--max_rounds", type=int, default=50, help="Limite superior de rodadas para tentar (para parar em 404)")
        parser.add_argument("--dry_run", action="store_true")

    def handle(self, *args, **options):
        season_year: int = options["season"]
        max_rounds: int = options["max_rounds"]
        dry_run: bool = options["dry_run"]

        season_code = f"{season_year-1}-{season_year}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.worldfootball.net/",
        }

        league, _ = League.objects.get_or_create(name="First League", country="Republica Tcheca")
        season_obj, _ = Season.objects.get_or_create(year=season_year)

        total_saved = 0
        for rnd in range(1, max_rounds + 1):
            url = f"https://www.worldfootball.net/schedule/cze-1-liga-{season_code}-spieltag/{rnd}/"
            self.stdout.write(self.style.HTTP_INFO(f"Rodada {rnd}: {url}"))
            try:
                r = requests.get(url, headers=headers, timeout=25)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Falha ao acessar {url}: {e}"))
                break

            if r.status_code == 404:
                self.stdout.write(self.style.WARNING(f"Fim das rodadas (404 em {rnd})."))
                break
            if r.status_code != 200:
                self.stdout.write(self.style.WARNING(f"Ignorando rodada {rnd}: status {r.status_code}"))
                continue

            try:
                tables = pd.read_html(r.text)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"read_html falhou na rodada {rnd}: {e}"))
                continue

            target = None
            for t in tables:
                cols = [str(c).strip().lower() for c in t.columns.tolist()]
                if "result" in cols and (("home" in cols) or ("team 1" in cols)) and (("away" in cols) or ("team 2" in cols)):
                    target = t
                    break
            if target is None:
                # fallback: algumas páginas usam duas primeiras colunas como times e uma coluna 'Result'
                for t in tables:
                    cols = [str(c).strip().lower() for c in t.columns.tolist()]
                    if "result" in cols and len(cols) >= 3:
                        target = t
                        break

            if target is None:
                self.stdout.write(self.style.WARNING(f"Rodada {rnd}: tabela de jogos não encontrada, pulando."))
                continue

            # localizar índices de colunas
            cols = [str(c).strip() for c in target.columns.tolist()]
            def idx_of(*names):
                for i, c in enumerate(cols):
                    lc = c.lower()
                    for n in names:
                        if n in lc:
                            return i
                return None

            i_home = idx_of("home", "team 1")
            i_away = idx_of("away", "team 2", "guest team")
            i_res = idx_of("result")
            i_date = idx_of("date")

            saved_this_round = 0
            for _, row in target.iterrows():
                vals = [str(x).strip() for x in row.values.tolist()]
                try:
                    home = vals[i_home] if i_home is not None else vals[0]
                    away = vals[i_away] if i_away is not None else vals[1]
                    res = vals[i_res] if i_res is not None else vals[2]
                    if not home or not away or home == "nan" or away == "nan":
                        continue

                    # resultado principal (ex: 2:1 (1:0) -> 2:1)
                    main_res = res.split()[0].replace("–", ":").replace("-", ":")
                    if ":" not in main_res:
                        continue
                    hg_str, ag_str = main_res.split(":")[:2]
                    hg = int(hg_str)
                    ag = int(ag_str)

                    # data (opcional)
                    dt_aware: Optional[datetime] = None
                    if i_date is not None:
                        dt_aware = self._parse_date(vals[i_date], season_year)

                    if not dry_run:
                        home_t, _ = Team.objects.get_or_create(name=home, league=league)
                        away_t, _ = Team.objects.get_or_create(name=away, league=league)
                        if home_t == away_t:
                            continue
                        defaults = {"home_score": hg, "away_score": ag, "status": "Finished"}
                        if dt_aware:
                            defaults["date"] = dt_aware
                        Match.objects.update_or_create(
                            league=league,
                            season=season_obj,
                            home_team=home_t,
                            away_team=away_t,
                            defaults=defaults,
                        )
                    saved_this_round += 1
                except Exception:
                    continue

            total_saved += saved_this_round
            self.stdout.write(self.style.SUCCESS(f"Rodada {rnd}: jogos processados {saved_this_round} (acumulado: {total_saved})"))

        self.stdout.write(self.style.SUCCESS(f"Total de jogos processados: {total_saved}"))

    def _parse_date(self, val: str, season_year: int) -> Optional[datetime]:
        if not val:
            return None
        patterns = ["%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%y", "%d.%m.%y"]
        for fmt in patterns:
            try:
                dt = datetime.strptime(val.strip(), fmt)
                return timezone.make_aware(dt, pytz.UTC)
            except Exception:
                continue
        return None
