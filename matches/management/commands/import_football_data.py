import os
import csv
import sys
from datetime import datetime
from io import StringIO

import pytz
import requests
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import League, Team, Match, Season
from matches.utils import normalize_team_name

# Force flush
sys.stdout.reconfigure(line_buffering=True)


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

    # Apenas as 10 grandes ligas europeias com CSVs por temporada em football-data.co.uk.
    # Ligas gerenciadas por outros scrapers (Austria/Sofascore, Australi/Sofascore,
    # Brasil/api-football, Argentina/scripts próprios, Suíça+Dinamarca+Tcheca/soccerstats)
    # NÃO devem ser incluídas aqui para evitar conflitos de dados.
    LEAGUE_MAPPING = {
        'E0':  ('Premier League',    'Inglaterra',  1),
        'SP1': ('La Liga',           'Espanha',     1),
        'D1':  ('Bundesliga',        'Alemanha',    1),
        'I1':  ('Serie A',           'Italia',      1),
        'F1':  ('Ligue 1',           'Franca',      1),
        'N1':  ('Eredivisie',        'Holanda',     1),
        'B1':  ('Pro League',        'Belgica',     1),
        'P1':  ('Primeira Liga',     'Portugal',    1),
        'T1':  ('Super Lig',         'Turquia',     1),
        'G1':  ('Super League',      'Grecia',      1),
    }

    def handle(self, *args, **options):
        self.stdout.write("--- Starting Import ---")
        root = options.get("root")
        division = options["division"]
        min_year = options["min_year"]

        if division == 'ALL':
            for div_code in self.LEAGUE_MAPPING.keys():
                self.stdout.write(self.style.WARNING(f"\n>>> Iniciando processamento para divisão: {div_code}"))
                self.process_division(div_code, min_year, root)
        else:
            if division not in self.LEAGUE_MAPPING:
                self.stdout.write(self.style.ERROR(
                    f"Divisão '{division}' não está no LEAGUE_MAPPING. "
                    f"Ligas suportadas: {', '.join(self.LEAGUE_MAPPING.keys())}"
                ))
                return
            self.process_division(division, min_year, root)


    def process_division(self, division, min_year, root):
        if division not in self.LEAGUE_MAPPING:
            self.stdout.write(self.style.ERROR(f"Divisão '{division}' não mapeada. Adicione ao LEAGUE_MAPPING."))
            return

        mapping = self.LEAGUE_MAPPING[division]
        league_name, country_name, division_level = mapping

        self.stdout.write(self.style.WARNING(f"Importando para: {league_name} ({country_name}) - Div {division_level}"))

        league, _ = League.objects.get_or_create(
            name=league_name, country=country_name, division=division_level
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

        all_processed_seasons = set()

        if use_files:
            for fname in os.listdir(root):
                if not fname.lower().endswith(".csv"):
                    continue
                path = os.path.join(root, fname)
                total_files += 1
                self.stdout.write(self.style.SUCCESS(f"Processando arquivo: {fname}"))
                try:
                    with open(path, newline="", encoding="utf-8-sig") as f:
                        reader = csv.DictReader(f)
                        r, c, u = self._process_reader(
                            reader, division, min_year, league, all_processed_seasons
                        )
                        total_rows += r
                        created_matches += c
                        updated_matches += u
                except Exception as e:
                     self.stdout.write(self.style.ERROR(f"Erro ao processar {fname}: {e}"))

        else:
            current_year = timezone.now().year
            end_year = current_year + 1
            seasons_to_process = range(min_year, end_year + 1)

            for season_year in seasons_to_process:
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
                
                # Handle BOM correctly by forcing utf-8-sig
                try:
                    content = resp.content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    content = resp.text

                reader = csv.DictReader(StringIO(content))
                r, c, u = self._process_reader(reader, division, min_year, league, all_processed_seasons)
                total_rows += r
                created_matches += c
                updated_matches += u

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Importação concluída"))
        self.stdout.write(f"Arquivos CSV processados: {total_files}")
        self.stdout.write(f"Linhas lidas: {total_rows}")
        self.stdout.write(f"Jogos criados: {created_matches}")
        self.stdout.write(f"Jogos atualizados: {updated_matches}")

        if all_processed_seasons:
            self.stdout.write(self.style.WARNING(f"\nRecalculando tabelas para temporadas: {sorted(list(all_processed_seasons))}"))
            for s_year in sorted(list(all_processed_seasons)):
                try:
                    self.stdout.write(f" -> Recalculando {league.name} ({league.country}) - {s_year}...")
                    call_command('recalculate_standings', league_name=league.name, country=league.country, season_year=s_year)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Erro ao recalcular {s_year}: {e}"))

    def _process_reader(self, reader, division, min_year, league, processed_seasons_set=None):
        rows = 0
        created = 0
        updated = 0
        
        # Determine expected division value
        # BRA.csv usually has 'Serie A' or 'BRA' in League column?
        # Based on file check: "League" column had "Serie A"
        # "Country" had "Brazil"
        
        # We need to adapt because standard football-data.co.uk uses 'Div' column (E0, etc.)
        # But BRA.csv uses 'League' and 'Country'
        
        # Read all rows first to handle iterator
        rows_list = list(reader)
        self.stdout.write(f"DEBUG: Found {len(rows_list)} rows in CSV")
        if rows_list:
            self.stdout.write(f"DEBUG: First row keys: {list(rows_list[0].keys())}")
        
        for row in rows_list:
            # Normalize keys to remove potential whitespace (e.g. "League " -> "League")
            row = {k.strip(): v for k, v in row.items() if k}


            rows += 1
            
            # Check division/league match — standard format for the 10 core leagues
            div = row.get("Div")
            if div != division:
                continue

            date_str = row.get("Date") or row.get("DATE")
            if not date_str:
                continue
            match_date = self._parse_date(date_str)
            if not match_date:
                continue

            # Parse Time
            time_str = row.get("Time")
            if time_str:
                try:
                    hour, minute = map(int, time_str.split(":"))
                    # date is timezone aware (UTC) from _parse_date
                    # replace needs naive or aware? _parse_date returns aware
                    # But replacing hour/minute on aware datetime works if timezone is preserved
                    # match_date is likely UTC. 
                    match_date = match_date.replace(hour=hour, minute=minute)
                except ValueError:
                    pass

            # Season determination
            season_val = row.get("Season")
            season_year = None
            
            if season_val:
                try:
                    # Try plain integer (e.g. "2026")
                    season_year = int(season_val)
                except ValueError:
                    # Try split format (e.g. "2012/2013") -> use the second year
                    if "/" in season_val:
                        parts = season_val.split("/")
                        if len(parts) == 2:
                            try:
                                season_year = int(parts[1])
                            except ValueError:
                                pass
            
            if not season_year:
                 season_year = self._season_year_from_date(match_date, division=div)
            if season_year < min_year:
                continue
            
            season, _ = Season.objects.get_or_create(year=season_year)

            home_name = row.get("HomeTeam") or row.get("Home")
            away_name = row.get("AwayTeam") or row.get("Away")
            if not home_name or not away_name:
                continue

            home_name = normalize_team_name(home_name)
            away_name = normalize_team_name(away_name)

            if season_year == 2017 and (created + updated) < 5:
                self.stdout.write(f"DEBUG: Creating/Getting teams: '{home_name}', '{away_name}' for league '{league.name}'")

            home_team, _ = Team.objects.get_or_create(name=home_name, league=league)
            away_team, _ = Team.objects.get_or_create(name=away_name, league=league)

            match_date_aware = match_date
            if timezone.is_naive(match_date_aware):
                match_date_aware = timezone.make_aware(match_date_aware, pytz.UTC)

            if not season_year:
                 season_year = self._season_year_from_date(match_date, division=div or division)
            if season_year < min_year:
                continue
            
            # DEBUG: Always print first few processed rows
            if (created + updated) < 5:
                 self.stdout.write(f"DEBUG: Processing row {rows}. Year: {season_year}. Teams: {home_name} v {away_name}")
            
            # Tenta pegar FTHG/FTAG (padrão europeu) ou HG/AG (padrão sul-americano)
            raw_fthg = row.get("FTHG") or row.get("HG")
            raw_ftag = row.get("FTAG") or row.get("AG")
            
            fthg = self._to_int(raw_fthg)
            ftag = self._to_int(raw_ftag)

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

            status = "Scheduled"
            if fthg is not None and ftag is not None:
                status = "Finished"

            defaults = {
                "date": match_date_aware,
                "status": status,
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

            # Try to find match by date (ignoring time)
            # IMPORTANT: For multi-round leagues (Switzerland, Austria, etc), we must respect existing matches
            # from SoccerStats scraper.
            # If a match exists with the same teams and roughly same date, we update it.
            # BUT if we are importing from CSV and the match is NOT found by date, 
            # we should be careful about creating it if it might be a duplicate with different date.
            
            # Logic similar to scrape_soccerstats_history: check date proximity
            from datetime import timedelta
            start_range = match_date_aware - timedelta(days=5)
            end_range = match_date_aware + timedelta(days=5)

            match = Match.objects.filter(
                league=league,
                home_team=home_team,
                away_team=away_team,
                date__range=(start_range, end_range)
            ).first()

            if match:
                # If match exists (likely from SoccerStats or previous import), we update stats only
                # We do NOT overwrite date unless it was None
                # We respect the high-quality data from SoccerStats if available
                
                # Merge logic: prioritize existing non-null values
                if match.home_score is None and fthg is not None:
                    match.home_score = fthg
                if match.away_score is None and ftag is not None:
                    match.away_score = ftag
                if match.status == 'Scheduled' and status == 'Finished':
                    match.status = status
                
                # Update detailed stats (shots, etc) if available in CSV and missing in DB
                if match.home_shots is None and hs is not None: match.home_shots = hs
                if match.away_shots is None and ast is not None: match.away_shots = ast
                if match.home_shots_on_target is None and hst is not None: match.home_shots_on_target = hst
                if match.away_shots_on_target is None and ast_on is not None: match.away_shots_on_target = ast_on
                
                # Atualiza a temporada caso tenha mudado (ex: correção de lógica)
                if match.season != season:
                    match.season = season
                match.save()
                updated += 1
            else:
                # Match not found. 
                # Check for "orphan" match (same teams, same season, no date)
                orphan = Match.objects.filter(
                    league=league,
                    season=season,
                    home_team=home_team,
                    away_team=away_team,
                    date__isnull=True
                ).first()
                
                if orphan:
                    orphan.date = match_date_aware
                    orphan.home_score = fthg
                    orphan.away_score = ftag
                    orphan.status = status
                    orphan.save()
                    updated += 1
                else:
                    # Create new match
                    Match.objects.create(
                        league=league,
                        season=season,
                        home_team=home_team,
                        away_team=away_team,
                        **defaults
                    )
                    created += 1

            if processed_seasons_set is not None and season_year:
                processed_seasons_set.add(season_year)



        return rows, created, updated

    def _parse_date(self, value):
        value = value.strip()
        for fmt in ("%d/%m/%y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    def _season_year_from_date(self, dt, division=None):
        """Para as 10 ligas core (todas europeias, temporada Ago-Maio):
        Se o jogo for em Agosto ou depois, pertence à temporada do ano seguinte."""
        year = dt.year
        if dt.month >= 8:
            return year + 1
        return year

    def _build_url(self, season_year, division):
        """Constrói URL no formato football-data.co.uk por temporada.
        Ex: 2024/2025 → /mmz4281/2425/E0.csv"""
        yy_end = season_year % 100
        yy_start = (season_year - 1) % 100
        code = f"{yy_start:02d}{yy_end:02d}"
        base = "https://www.football-data.co.uk/mmz4281"
        url = f"{base}/{code}/{division}.csv"
        return url, code

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
