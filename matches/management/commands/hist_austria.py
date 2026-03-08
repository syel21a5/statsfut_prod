"""
hist_austria.py
===============
Importa dados históricos da Bundesliga austríaca usando o projeto openfootball
(https://github.com/openfootball/austria) via raw.githubusercontent.com.

✅ Sem scraping de HTML — apenas GET em arquivos de texto no GitHub (sem bloqueio)
✅ Cobertura: temporadas 2015/16 a 2025/26

Uso:
    python manage.py hist_austria                         # importa 2016→2025
    python manage.py hist_austria --seasons 2024 2025     # temporadas específicas
    python manage.py hist_austria --dry_run               # sem salvar no BD

Formato do arquivo openfootball (exemplo):
    Matchday 1
    [Fri Jul/26]
      20.45  Rapid Wien    0-2 (0-1)  RB Salzburg
      ...
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
TEAM_MAPPING = {
    "SK Rapid Wien": "Rapid Vienna",
    "SK Sturm Graz": "Sturm Graz",
    "SK Austria Klagenfurt": "Austria Klagenfurt",
    "RB Salzburg": "Red Bull Salzburg",
    "FC Red Bull Salzburg": "Red Bull Salzburg",
    "Red Bull Salzburg": "Red Bull Salzburg",
    "LASK": "LASK",
    "LASK Linz": "LASK",
    "Sturm Graz": "Sturm Graz",
    "Wolfsberger AC": "Wolfsberger AC",
    "WAC": "Wolfsberger AC",
    "TSV Hartberg": "TSV Hartberg",
    "SCR Altach": "SC Rheindorf Altach",
    "Altach": "SC Rheindorf Altach",
    "FC Admira Wacker": "Admira Wacker Modling",
    "Admira Wacker": "Admira Wacker Modling",
    "SKN St. Pölten": "SKN St. Polten",
    "SKN St. Polten": "SKN St. Polten",
    "SV Mattersburg": "SC Mattersburg",
    "FC Flyeralarm Admira": "Admira Wacker Modling",
    "Admira": "Admira Wacker Modling",
    "SKN": "SKN St. Polten",
    "SV Ried": "SV Ried",
    "FC Ried": "SV Ried",
    "WSG Tirol": "WSG Tirol",
    "WSG Wattens": "WSG Tirol",
    "Austria Lustenau": "Austria Lustenau",
    "FC Austria Lustenau": "Austria Lustenau",
    "BW Linz": "Blau-Weiss Linz",
    "Blau-Weiß Linz": "Blau-Weiss Linz",
    "Blau-Weiss Linz": "Blau-Weiss Linz",
    "FC Blau-Weiß Linz": "Blau-Weiss Linz",
    "GAK": "GAK 1902",
    "GAK 1902": "GAK 1902",
    "FC Juniors OÖ": "FC Juniors OO",
    "FACC Wels": "FACC Wels",
    "FC Wacker Innsbruck": "Wacker Innsbruck",
    "Wacker Innsbruck": "Wacker Innsbruck",
    "SC Wiener Neustadt": "Wiener Neustadt",
    "FC Groedig": "FC Grodig",
    "FC Grödig": "FC Grodig",
}

# Temporadas openfootball → ano de término (end_year)
# Chave = "YYYY-YY" (prefixo do diretório); Valor = end_year para Season
SEASON_MAP = {
    "2015-16": 2016,
    "2016-17": 2017,
    "2017-18": 2018,
    "2018-19": 2019,
    "2019-20": 2020,
    "2020-21": 2021,
    "2021-22": 2022,
    "2022-23": 2023,
    "2023-24": 2024,
    "2024-25": 2025,
    "2025-26": 2026,
}

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/openfootball/austria/master"
LEAGUE_NAME = "Bundesliga"
LEAGUE_COUNTRY = "Austria"


class Command(BaseCommand):
    help = "Importa histórico da Bundesliga austríaca via openfootball (GitHub)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--seasons",
            nargs="+",
            type=int,
            default=list(range(2016, 2026)),
            help="Anos de TÉRMINO da temporada (ex: 2024 = 2023/24). Default: 2016-2025.",
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

        league, _ = League.objects.get_or_create(
            name=LEAGUE_NAME, country=LEAGUE_COUNTRY
        )
        self.stdout.write(self.style.SUCCESS(f"✅ Liga: {league}"))

        # Monta dicionário invertido: end_year → season_key
        end_year_to_key = {v: k for k, v in SEASON_MAP.items()}

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; statsfut-importer/1.0)",
        }

        total = 0
        for end_year in seasons:
            season_key = end_year_to_key.get(end_year)
            if not season_key:
                self.stdout.write(self.style.WARNING(f"⚠️  Temporada {end_year} não mapeada. Use entre 2016-2026."))
                continue

            url = f"{GITHUB_RAW_BASE}/{season_key}/1-bundesliga.txt"
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

            season_obj = Season.objects.filter(year=end_year).first()
            if not season_obj:
                season_obj = Season.objects.create(year=end_year)
            count = self._parse_and_import(
                resp.text, league, season_obj, end_year, dry_run
            )
            total += count
            self.stdout.write(self.style.SUCCESS(f"   ✅ {count} partidas importadas"))

            if not dry_run and recalc and count > 0:
                try:
                    call_command(
                        "recalculate_standings",
                        league_name=league.name,
                        country=league.country,
                        season_year=end_year,
                    )
                    self.stdout.write(f"   📊 Standings recalculados para {end_year-1}/{end_year}")
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Standings falhou: {exc}"))

            time.sleep(random.uniform(0.5, 1.5))

        self.stdout.write(self.style.SUCCESS(f"\n🏁 Concluído! Total: {total} partidas"))

    # ── Parser do formato openfootball ──────────────────────────────────────────

    def _parse_and_import(
        self,
        text: str,
        league: League,
        season_obj: Season,
        end_year: int,
        dry_run: bool,
    ) -> int:
        """
        Parseia o formato txt do openfootball.
        
        Exemplo de linhas relevantes:
          [Fri Jul/26]
            20.45  Rapid Wien    0-2 (0-1)  RB Salzburg
        """
        count = 0
        current_date: Optional[datetime] = None

        # Regex para linha de data: [Fri Jul/26] ou Sat Jul/22 2017
        date_re = re.compile(
            r"(\w{3})/(\d{1,2})(?:\s+(\d{4}))?"
        )
        # Pattern A (Old): HH.MM  Home Team  X-Y (A-B)  Away Team
        # Example: 20.45  Rapid Wien    0-2 (0-1)  RB Salzburg
        re_a = re.compile(
            r"^\s+(?:\d{1,2}[.:]\d{2}\s+)?(.+?)\s+(\d+)-(\d+)(?:\s*\(\d+-\d+\))?\s+(.+?)\s*$"
        )

        # Pattern B (New): HH.MM  Home Team  v  Away Team  X-Y (A-B)
        # Example: 20.30  Grazer AK               v RB Salzburg              2-3 (2-3)
        re_b = re.compile(
            r"^\s+(?:\d{1,2}[.:]\d{2}\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)-(\d+)(?:\s*\(\d+-\d+\))?\s*$"
        )

        month_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
        }

        for raw_line in text.splitlines():
            line = raw_line.rstrip()

            # ── Detecta linha de data ────────────────────────────────────────
            dm = date_re.search(line)
            if dm:
                month_str = dm.group(1)[:3].capitalize()
                day = int(dm.group(2))
                month = month_map.get(month_str)
                if month:
                    # Determina o ano correto da data
                    year_for_date = end_year - 1 if month >= 7 else end_year
                    try:
                        dt = datetime(year_for_date, month, day)
                        current_date = timezone.make_aware(dt, pytz.UTC)
                    except ValueError:
                        current_date = None
                continue

            # ── Detecta linha de partida ────────────────────────────────────
            # Tenta Pattern B primeiro (mais específico)
            mm = re_b.match(line)
            if mm:
                home_raw = mm.group(1).strip()
                away_raw = mm.group(2).strip()
                h_score  = int(mm.group(3))
                a_score  = int(mm.group(4))
            else:
                # Tenta Pattern A
                mm = re_a.match(line)
                if mm:
                    home_raw = mm.group(1).strip()
                    h_score  = int(mm.group(2))
                    a_score  = int(mm.group(3))
                    away_raw = mm.group(4).strip()
                else:
                    continue

            # Ignora linhas de cabeçalho ou artefatos
            if not home_raw or not away_raw:
                continue
            # Descarta se parece horário
            if re.match(r"^\d+[.:]\d+$", home_raw):
                continue

            home_name = TEAM_MAPPING.get(home_raw, home_raw)
            away_name = TEAM_MAPPING.get(away_raw, away_raw)

            if dry_run:
                date_str = current_date.strftime("%d/%m/%Y") if current_date else "?"
                self.stdout.write(
                    f"   [DRY] {date_str}  {home_name} {h_score}-{a_score} {away_name}"
                )
                count += 1
                continue

            try:
                home_team, _ = Team.objects.get_or_create(name=home_name, league=league)
                away_team, _ = Team.objects.get_or_create(name=away_name, league=league)

                if home_team == away_team:
                    continue

                defaults = {
                    "home_score": h_score,
                    "away_score": a_score,
                    "status": "Finished",
                }
                if current_date:
                    defaults["date"] = current_date

                # Busca partida existente (janela ±3 dias)
                existing = None
                if current_date:
                    w_start = current_date - timezone.timedelta(days=3)
                    w_end   = current_date + timezone.timedelta(days=3)
                    existing = Match.objects.filter(
                        league=league,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        date__range=(w_start, w_end),
                    ).first()

                if not existing:
                    existing = Match.objects.filter(
                        league=league,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        date__isnull=True,
                    ).first()

                if existing:
                    for k, v in defaults.items():
                        setattr(existing, k, v)
                    existing.save()
                else:
                    Match.objects.create(
                        league=league,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        **defaults,
                    )
                count += 1

            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Linha ignorada: {home_raw} vs {away_raw} → {exc}"))
                continue

        return count
