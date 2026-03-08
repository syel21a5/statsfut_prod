"""
hist_australia.py
=================
Importa dados históricos da A-League australiana usando o projeto openfootball/world
(https://github.com/openfootball/world/tree/master/pacific/australia)

✅ Sem scraping de HTML — apenas GET em arquivos de texto no GitHub
✅ Cobertura: temporadas 2018/19 a 2024/25

Uso:
    python manage.py hist_australia                         # importa 2019→2025
    python manage.py hist_australia --seasons 2024 2025     # temporadas específicas
    python manage.py hist_australia --dry_run               # sem salvar no BD
"""

import re
import time
import random
from datetime import datetime
from typing import Optional

import requests
import pytz
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone

from matches.models import League, Match, Season, Team

# ── Mapeamento: nomes do openfootball → nomes canônicos no BD ──────────────────
# BD Teams (A-League Men):
# Adelaide United, Auckland FC, Brisbane Roar, Central Coast Mariners,
# Macarthur FC, Melbourne City, Melbourne Victory, Newcastle Jets FC,
# Perth Glory, Sydney FC, Wellington Phoenix, Western Sydney Wanderers, Western United
TEAM_MAPPING = {
    "Melbourne City FC": "Melbourne City",
    "Melbourne City": "Melbourne City",
    "Newcastle United Jets": "Newcastle Jets FC",
    "Newcastle Jets FC": "Newcastle Jets FC",
    "Wellington Phoenix FC": "Wellington Phoenix",
    "Wellington Phoenix": "Wellington Phoenix",
    "Western Sydney Wanderers": "Western Sydney Wanderers",
    "WS Wanderers": "Western Sydney Wanderers",
    "CC Mariners": "Central Coast Mariners",
    "Central Coast Mariners": "Central Coast Mariners",
    "Brisbane Roar": "Brisbane Roar",
    "Sydney FC": "Sydney FC",
    "Adelaide United": "Adelaide United",
    "Melbourne Victory": "Melbourne Victory",
    "Perth Glory": "Perth Glory",
    "Macarthur FC": "Macarthur FC",
    "Western United": "Western United",
    "Auckland FC": "Auckland FC",
}

# Temporadas openfootball → ano de término (end_year)
SEASON_MAP = {
    "2018-19": 2019,
    "2019-20": 2020,
    "2020-21": 2021,
    "2021-22": 2022,
    "2022-23": 2023,
    "2023-24": 2024,
    "2024-25": 2025,
}

# Link direto no repositório 'world'
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/openfootball/world/master/pacific/australia"
LEAGUE_NAME = "A-League Men"
LEAGUE_COUNTRY = "Australia"

class Command(BaseCommand):
    help = "Importa histórico da A-League australiana via openfootball (GitHub)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--seasons",
            nargs="+",
            type=int,
            default=list(range(2019, 2026)),
            help="Anos de TÉRMINO da temporada (ex: 2024 = 2023/24). Default: 2019-2025.",
        )
        parser.add_argument(
            "--dry_run",
            action="store_true",
            help="Mostra o que seria importado sem salvar no banco.",
        )
        parser.add_argument(
            "--recalc",
            action="store_true",
            default=True,
            help="Recalcula standings após importar (default: True).",
        )

    def handle(self, *args, **options):
        seasons: list[int] = sorted(options["seasons"])
        dry_run: bool = options["dry_run"]
        recalc: bool = options["recalc"]

        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  DRY RUN – nenhum dado será salvo."))

        # Pega a liga correta (A-League Men ID 9)
        league = League.objects.filter(name=LEAGUE_NAME, country=LEAGUE_COUNTRY).first()
        if not league:
            # Tenta buscar por ID se o nome for ligeiramente diferente
            league = League.objects.filter(id=9).first()
            
        if not league:
            self.stdout.write(self.style.ERROR(f"❌ Liga '{LEAGUE_NAME}' não encontrada no banco."))
            return

        self.stdout.write(self.style.SUCCESS(f"✅ Liga: {league}"))

        end_year_to_key = {v: k for k, v in SEASON_MAP.items()}
        headers = {"User-Agent": "Mozilla/5.0"}

        total = 0
        for end_year in seasons:
            season_key = end_year_to_key.get(end_year)
            if not season_key:
                self.stdout.write(self.style.WARNING(f"⚠️  Temporada {end_year} não mapeada."))
                continue

            url = f"{GITHUB_RAW_BASE}/{season_key}_au1.txt"
            self.stdout.write(f"\n📥 Temporada {end_year-1}/{end_year}: {url}")

            try:
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.status_code == 404:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Arquivo não encontrado (404): {url}"))
                    continue
                if resp.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"   ❌ HTTP {resp.status_code}"))
                    continue
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"   ❌ Erro de rede: {exc}"))
                continue

            # Garante a Season
            season_obj = Season.objects.filter(year=end_year).first()
            if not season_obj:
                season_obj = Season.objects.create(year=end_year)

            count = self._parse_and_import(
                resp.text, league, season_obj, end_year, dry_run
            )
            total += count
            self.stdout.write(self.style.SUCCESS(f"   ✅ {count} partidas processadas"))

            if not dry_run and recalc and count > 0:
                try:
                    call_command(
                        "recalculate_standings",
                        league_name=league.name,
                        country=league.country,
                        season_year=end_year,
                    )
                    self.stdout.write(f"   📊 Standings recalculados.")
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Standings falhou: {exc}"))

            time.sleep(random.uniform(0.5, 1.0))

        self.stdout.write(self.style.SUCCESS(f"\n🏁 Concluído! Total: {total} partidas"))

    def _parse_and_import(self, text, league, season_obj, end_year, dry_run):
        count = 0
        current_date = None

        # Regex para datas (ex: Fri Oct/20 2023 ou Sat Oct/21)
        # Mais flexível para suportar com ou sem colchetes
        date_re = re.compile(r"(\w{3})\s+(\w{3})/(\d{1,2})(?:\s+(\d{4}))?")
        
        # Pattern B (com 'v'): Team A v Team B Score
        re_b = re.compile(
            r"^\s+(?:\d{1,2}[.:]\d{2}\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)-(\d+)(?:\s*\(\d+-\d+\))?\s*$"
        )
        
        # Pattern A (sem 'v'): Team A Score Team B
        re_a = re.compile(
            r"^\s+(?:\d{1,2}[.:]\d{2}\s+)?(.+?)\s+(\d+)-(\d+)(?:\s*\(\d+-\d+\))?\s+(.+?)\s*$"
        )

        month_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
        }

        for line in text.splitlines():
            line = line.rstrip()
            if not line: continue

            # Detecta data
            dm = date_re.search(line)
            if dm and not re_a.search(line) and not re_b.search(line):
                month_str = dm.group(2).capitalize()
                day = int(dm.group(3))
                month = month_map.get(month_str)
                if month:
                    year_for_date = end_year - 1 if month >= 7 else end_year
                    try:
                        dt = datetime(year_for_date, month, day)
                        current_date = timezone.make_aware(dt, pytz.UTC)
                    except ValueError:
                        current_date = None
                continue

            # Detecta jogo
            mm = re_b.match(line)
            if mm:
                home_raw, away_raw = mm.group(1).strip(), mm.group(2).strip()
                h_score, a_score = int(mm.group(3)), int(mm.group(4))
            else:
                mm = re_a.match(line)
                if mm:
                    home_raw, h_score, a_score, away_raw = mm.group(1).strip(), int(mm.group(2)), int(mm.group(3)), mm.group(4).strip()
                else:
                    continue

            home_name = TEAM_MAPPING.get(home_raw, home_raw)
            away_name = TEAM_MAPPING.get(away_raw, away_raw)

            if dry_run:
                self.stdout.write(f"   [DRY] {current_date.strftime('%Y-%m-%d') if current_date else '?'} {home_name} {h_score}-{a_score} {away_name}")
                count += 1
                continue

            try:
                home_team, _ = Team.objects.get_or_create(name=home_name, league=league)
                away_team, _ = Team.objects.get_or_create(name=away_name, league=league)

                defaults = {
                    "home_score": h_score,
                    "away_score": a_score,
                    "status": "Finished",
                }
                if current_date:
                    defaults["date"] = current_date

                # Busca existente para evitar duplicatas
                existing = None
                if current_date:
                    w_start = current_date - timezone.timedelta(days=2)
                    w_end   = current_date + timezone.timedelta(days=2)
                    existing = Match.objects.filter(
                        league=league, season=season_obj,
                        home_team=home_team, away_team=away_team,
                        date__range=(w_start, w_end)
                    ).first()

                if existing:
                    for k, v in defaults.items(): setattr(existing, k, v)
                    existing.save()
                else:
                    Match.objects.create(league=league, season=season_obj, home_team=home_team, away_team=away_team, **defaults)
                count += 1
            except Exception as e:
                self.stdout.write(f"   ⚠️ Erro: {e}")

        return count
