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

        # Heurística por linhas: encontrar tabela onde cada linha tem [Team] + sequência de inteiros (GP, W, D, L, GF, GA, GD?, Pts)
        def to_int(s: str) -> Optional[int]:
            try:
                s = s.replace('+', '').replace('–', '-').replace('—', '-').replace('−', '-')
                # remove sufixos como '%'
                s = ''.join(ch for ch in s if ch.isdigit() or ch in {'-', '+'})
                if s == '' or s == '-':
                    return None
                return int(s)
            except Exception:
                return None

        def extract_rows(df: pd.DataFrame):
            result = []
            for _, row in df.iterrows():
                cells = [str(x).strip() for x in row.values.tolist()]
                # encontra nome do time: primeira célula "não numérica" com letras
                team_idx = None
                for i, c in enumerate(cells):
                    if not c:
                        continue
                    cl = c.lower()
                    if cl in {'#', 'avg', 'average'}:
                        continue
                    # tem alguma letra?
                    if any(ch.isalpha() for ch in c):
                        # evite cabeçalhos
                        if c.lower() in {'team', 'teams'}:
                            continue
                        team_idx = i
                        break
                if team_idx is None:
                    continue
                team_name = cells[team_idx]
                # após o nome do time, coletar inteiros
                nums = []
                for c in cells[team_idx+1:]:
                    v = to_int(c)
                    if v is not None:
                        nums.append(v)
                # precisamos pelo menos de GP,W,D,L,GF,GA e Pts (com ou sem GD no meio)
                if len(nums) < 7:
                    continue
                gp, w, d, l, gf, ga = nums[0], nums[1], nums[2], nums[3], nums[4], nums[5]
                # Pts pode estar na posição 6 (sem GD) ou 7 (com GD)
                pts = nums[7] if len(nums) >= 8 else nums[6]
                # sanity checks
                if not (0 <= gp <= 60 and 0 <= w <= 60 and 0 <= d <= 60 and 0 <= l <= 60 and 0 <= gf <= 200 and 0 <= ga <= 200 and 0 <= pts <= 120):
                    continue
                result.append((team_name, gp, w, d, l, gf, ga, pts))
            return result

        best_rows = []
        for t in tables:
            rows = extract_rows(t)
            if len(rows) > len(best_rows):
                best_rows = rows
        if not best_rows:
            self.stdout.write(self.style.ERROR("Não foi possível localizar a tabela de classificação."))
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

        rows = [(norm_team(t), gp, w, d, l, gf, ga, pts) for (t, gp, w, d, l, gf, ga, pts) in best_rows if t and t.lower() not in {"average", "averages"}]

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
