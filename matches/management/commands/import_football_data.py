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

        # Mapeamento Divisão -> (Liga, País)
        # Fonte: https://www.football-data.co.uk/notes.txt
        LEAGUE_MAPPING = {
            'E0': ('Premier League', 'Inglaterra'),
            'SP1': ('La Liga', 'Espanha'),
            'D1': ('Bundesliga', 'Alemanha'),
            'I1': ('Serie A', 'Italia'),
            'F1': ('Ligue 1', 'Franca'),
            'N1': ('Eredivisie', 'Holanda'),
            'B1': ('Pro League', 'Belgica'),
            'P1': ('Primeira Liga', 'Portugal'),
            'T1': ('Super Lig', 'Turquia'),
            'G1': ('Super League', 'Grecia'),
            'BRA': ('Brasileirão', 'Brasil'), # Added for Brazil
        }

        if division not in LEAGUE_MAPPING:
            self.stdout.write(self.style.ERROR(f"Divisão '{division}' não mapeada. Adicione ao LEAGUE_MAPPING."))
            return

        league_name, country_name = LEAGUE_MAPPING[division]
        
        self.stdout.write(self.style.WARNING(f"Importando para: {league_name} ({country_name})"))

        league, _ = League.objects.get_or_create(
            name=league_name, country=country_name
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
                try:
                    with open(path, newline="", encoding="utf-8-sig") as f:
                        reader = csv.DictReader(f)
                        r, c, u = self._process_reader(
                            reader, division, min_year, league
                        )
                        total_rows += r
                        created_matches += c
                        updated_matches += u
                except Exception as e:
                     self.stdout.write(self.style.ERROR(f"Erro ao processar {fname}: {e}"))

        else:
            current_year = timezone.now().year
            
            if division == 'BRA':
                # Brasil: arquivo único com todo o histórico. Processar apenas uma vez.
                seasons_to_process = [current_year]
                self.stdout.write(self.style.WARNING("Modo Brasil detectado: Processando arquivo único histórico (BRA.csv)."))
            else:
                # Europa: arquivos por temporada.
                # Ligas europeias terminam no ano seguinte (ex: 2025/2026 -> 2026)
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
                    # Fallback if it fails
                    content = resp.text

                reader = csv.DictReader(StringIO(content))
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
        
        # Determine expected division value
        # BRA.csv usually has 'Serie A' or 'BRA' in League column?
        # Based on file check: "League" column had "Serie A"
        # "Country" had "Brazil"
        
        # We need to adapt because standard football-data.co.uk uses 'Div' column (E0, etc.)
        # But BRA.csv uses 'League' and 'Country'
        
        # Read all rows first to handle iterator
        rows_list = list(reader)
        
        for row in rows_list:
            rows += 1
            
            # Check division/league match
            div = row.get("Div")
            
            if division == 'BRA':
                # Special handling for Brazil: requires League="Serie A" (or Country="Brazil")
                # BRA.csv usually has League="Serie A" and Country="Brazil"
                # Some rows might be other leagues if the file is mixed, but usually it's one league per file or specified
                
                # Check for explicit "Serie A" in League column
                league_col = row.get("League")
                country_col = row.get("Country")
                
                # If neither Div nor League is present, it's likely a bad row or different CSV format
                if not div and not league_col:
                    continue

                # If it's a standard football-data file, it might have Div='BRA' (unlikely, usually separate file)
                # But our target file has League='Serie A'
                if league_col == "Serie A" and country_col == "Brazil":
                    pass # Valid
                elif div == "BRA": 
                    pass # Valid if they add Div column later
                else:
                    continue # Skip invalid rows for BRA division
            else:
                # Standard handling for European leagues
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
            # BRA.csv has explicit 'Season' column!
            season_val = row.get("Season")
            if season_val:
                try:
                    season_year = int(season_val)
                except:
                     season_year = self._season_year_from_date(match_date, division)
            else:
                season_year = self._season_year_from_date(match_date, division)
            
            if season_year < min_year:
                continue

            season, _ = Season.objects.get_or_create(year=season_year)

            home_name = row.get("HomeTeam") or row.get("Home")
            away_name = row.get("AwayTeam") or row.get("Away")
            if not home_name or not away_name:
                continue

            # Mapeamento de nomes para evitar duplicatas
            mappings = {
                "Wolves": "Wolverhampton",
                "Man City": "Manchester City",
                "Man United": "Manchester Utd",
                "Newcastle": "Newcastle Utd",
                "Nott'm Forest": "Nottm Forest",
                "West Ham": "West Ham Utd",
                "Leeds": "Leeds Utd",
                "Sunderland AFC": "Sunderland",
                "Nottingham Forest FC": "Nottm Forest",
                
                # Brazil Mappings (Normalization)
                "Flamengo RJ": "Flamengo",
                "Botafogo RJ": "Botafogo",
                "CA Mineiro": "Atletico-MG",
                "Atletico Mineiro": "Atletico-MG",
                "CA Paranaense": "Athletico-PR",
                "Club Athletico Paranaense": "Athletico-PR",
                "Coritiba FBC": "Coritiba",
                "Chapecoense AF": "Chapecoense",
                "Chapecoense-SC": "Chapecoense",
                "Clube do Remo": "Remo",
                "Mirassol FC": "Mirassol",
                "RB Bragantino": "Bragantino",
                "Red Bull Bragantino": "Bragantino",
                "Sao Paulo FC": "Sao Paulo",
                "Santos FC": "Santos",
                "Gremio FBPA": "Gremio",
                "Cruzeiro EC": "Cruzeiro",
                "EC Vitoria": "Vitoria",
                "Vasco da Gama": "Vasco",
                "Cuiaba Esporte Clube": "Cuiaba",
                "America FC": "America-MG", 
                "America MG": "America-MG",
                "Goias EC": "Goias",
                "Ceara SC": "Ceara",
                "Fortaleza EC": "Fortaleza",
                "EC Bahia": "Bahia",
                "Sport Club do Recife": "Sport Recife",
                "Avai FC": "Avai",
                "Juventude RS": "Juventude",
                "CSA": "CSA",
            }
            
            home_name = mappings.get(home_name, home_name)
            away_name = mappings.get(away_name, away_name)

            home_team, _ = Team.objects.get_or_create(name=home_name, league=league)
            away_team, _ = Team.objects.get_or_create(name=away_name, league=league)

            match_date_aware = match_date
            if timezone.is_naive(match_date_aware):
                match_date_aware = timezone.make_aware(match_date_aware, pytz.UTC)

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
            match = Match.objects.filter(
                league=league,
                home_team=home_team,
                away_team=away_team,
                date__date=match_date_aware.date()
            ).first()

            if match:
                for key, value in defaults.items():
                    setattr(match, key, value)
                # Atualiza a temporada caso tenha mudado (ex: correção de lógica)
                if match.season != season:
                    match.season = season
                match.save()
                updated += 1
            else:
                Match.objects.create(
                    league=league,
                    season=season,
                    home_team=home_team,
                    away_team=away_team,
                    **defaults
                )
                created += 1

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
        year = dt.year
        # Se for Brasil, a temporada é o ano civil (Jan-Dez)
        if division == 'BRA':
            return year
            
        # Para ligas europeias (Ago-Maio), se for Ago+, é a temporada do ano seguinte
        if dt.month >= 8:
            return year + 1
        return year

    def _build_url(self, season_year, division):
        # Format: 2425 for 2024/2025
        # 2024 -> 2324 ? No, usually season_year is the END year for spanning leagues
        # For Brazil (calendar year), it might be just YYYY?
        # But football-data.co.uk uses standard directory structure mm/div.csv
        # However, for Extra leagues like BRA, it's often a single file 'new/BRA.csv'
        
        if division == 'BRA':
            # Special case for Brazil: single file URL
            return "https://www.football-data.co.uk/new/BRA.csv", "BRA"

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
