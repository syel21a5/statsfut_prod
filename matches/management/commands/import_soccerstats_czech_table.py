from typing import Optional

import pandas as pd
import requests
from django.core.management.base import BaseCommand

from matches.models import League, LeagueStanding, Season, Team


class Command(BaseCommand):
    help = "Importa a League Table da First League (República Tcheca) do SoccerStats (latest.asp) diretamente para LeagueStanding"

    def add_arguments(self, parser):
        parser.add_argument("--season_year", type=int, default=2026, help="Ano de término da temporada (ex: 2026)")
        parser.add_argument("--dry_run", action="store_true")

    def handle(self, *args, **options):
        season_year: int = options["season_year"]
        dry_run: bool = options["dry_run"]

        league, _ = League.objects.get_or_create(name="First League", country="Republica Tcheca")
        season, _ = Season.objects.get_or_create(year=season_year)

        url = "https://www.soccerstats.com/latest.asp?league=czechrepublic"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        }
        self.stdout.write(self.style.SUCCESS(f"Baixando: {url}"))
        r = requests.get(url, headers=headers, timeout=25)
        if r.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Falha ao acessar {url}: {r.status_code}"))
            return

        try:
            tables = pd.read_html(r.text)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"read_html falhou: {e}"))
            return

        target = None
        for t in tables:
            cols = [str(c).strip().lower() for c in t.columns.tolist()]
            if any(c in cols for c in ["team", "teams"]) and "gp" in cols and "pts" in cols:
                target = t
                break
        if target is None:
            self.stdout.write(self.style.ERROR("Não foi possível localizar a tabela de classificação."))
            return

        col_map = {c.lower(): i for i, c in enumerate([str(x).strip() for x in target.columns.tolist()])}
        def idx(*names) -> Optional[int]:
            for n in names:
                if n in col_map:
                    return col_map[n]
            return None

        i_team = idx("team", "teams")
        i_gp = idx("gp", "p", "played")
        i_w = idx("w", "won")
        i_d = idx("d", "drawn")
        i_l = idx("l", "lost")
        i_gf = idx("gf", "goals for")
        i_ga = idx("ga", "goals against")
        i_pts = idx("pts", "points")

        req = [i_team, i_gp, i_w, i_d, i_l, i_gf, i_ga, i_pts]
        if any(x is None for x in req):
            self.stdout.write(self.style.ERROR(f"Colunas esperadas não encontradas: {req}"))
            return

        mapping = {
            "Slavia Prague": "Slavia Prague",
            "Sparta Prague": "Sparta Prague",
            "Jablonec": "Jablonec",
            "Viktoria Plzen": "Viktoria Plzen",
            "Slovan Liberec": "Slovan Liberec",
            "Karvina": "Karvina",
            "Hradec Kralove": "Hradec Kralove",
            "Sigma Olomouc": "Sigma Olomouc",
            "Zlin": "Zlin",
            "Teplice": "Teplice",
            "Pardubice": "Pardubice",
            "Bohemians": "Bohemians",
            "Banik Ostrava": "Banik Ostrava",
            "Mlada Boleslav": "Mlada Boleslav",
            "Slovacko": "Slovacko",
            "Dukla Praha": "Dukla Praha",
        }
        def norm_team(name: str) -> str:
            name = (name or "").strip()
            return mapping.get(name, name)

        rows = []
        for _, row in target.iterrows():
            vals = [str(x).strip() for x in row.values.tolist()]
            try:
                team_name = norm_team(vals[i_team])
                if not team_name or team_name.lower() in {"average", "averages"}:
                    continue
                gp = int(float(vals[i_gp]))
                w = int(float(vals[i_w]))
                d = int(float(vals[i_d]))
                l = int(float(vals[i_l]))
                gf = int(float(vals[i_gf]))
                ga = int(float(vals[i_ga]))
                pts = int(float(vals[i_pts]))
                rows.append((team_name, gp, w, d, l, gf, ga, pts))
            except Exception:
                continue

        if not rows:
            self.stdout.write(self.style.ERROR("Nenhuma linha válida encontrada na tabela."))
            return

        if not dry_run:
            LeagueStanding.objects.filter(league=league, season=season).delete()

        created = 0
        pos_sorted = sorted(rows, key=lambda x: (-x[7], -(x[5] - x[6]), -x[5], x[0]))
        for idx, (team_name, gp, w, d, l, gf, ga, pts) in enumerate(pos_sorted, start=1):
            if dry_run:
                created += 1
                continue
            team, _ = Team.objects.get_or_create(name=team_name, league=league)
            LeagueStanding.objects.create(
                league=league,
                season=season,
                team=team,
                position=idx,
                played=gp,
                won=w,
                drawn=d,
                lost=l,
                goals_for=gf,
                goals_against=ga,
                points=pts,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Standings importados: {created}"))
        self.stdout.write(self.style.WARNING("Atenção: não rode recalculate_standings após este comando, senão a tabela volta a usar apenas jogos do banco."))
