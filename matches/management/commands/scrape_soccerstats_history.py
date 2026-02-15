
import os
import time
import random
import requests
import pandas as pd
from io import StringIO
from datetime import datetime
import pytz
from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from django.utils import timezone

class Command(BaseCommand):
    help = 'Scrape historical match results from SoccerStats.com'

    def add_arguments(self, parser):
        parser.add_argument('--years', nargs='+', type=int, help='Years to scrape (e.g. 2024 for 2023/24)')
        parser.add_argument('--csv_only', action='store_true', help='Save to CSV only, do not import to DB')

    def handle(self, *args, **kwargs):
        # Default to 2010-2025 if not specified
        years = kwargs['years'] or list(range(2010, 2026))
        csv_only = kwargs['csv_only']
        
        # Ensure export directory exists
        base_dir = "csv_exports"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # We process England and Brazil
        # SoccerStats URL patterns:
        # England: https://www.soccerstats.com/results.asp?league=england_2024 (for 2023/24)
        # Brazil: https://www.soccerstats.com/results.asp?league=brazil_2024 (for 2024)
        
        leagues = [
            {
                'name': 'Premier League',
                'country': 'Inglaterra',
                'url_base': 'england',
                'current_param': 'england' # For current season sometimes it's just 'england'
            },
            {
                'name': 'Brasileirão',
                'country': 'Brasil',
                'url_base': 'brazil',
                'current_param': 'brazil'
            }
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        for league_conf in leagues:
            if league_conf['name'] != 'Brasileirão': # Only process Brazil for now as requested
                continue

            self.stdout.write(self.style.SUCCESS(f"--- Processing {league_conf['name']} ---"))
            
            league_obj = None
            if not csv_only:
                league_obj, _ = League.objects.get_or_create(
                    name=league_conf['name'], 
                    country=league_conf['country']
                )

            for year in years:
                # Construct URL
                # For current season (2025), use the base URL without year suffix
                # For historical seasons, use the _YEAR format
                
                if league_conf['name'] == 'Brasileirão' and year == 2026:
                    # Force URL for current Brazil season
                    url = "https://www.soccerstats.com/results.asp?league=brazil"
                elif year == 2025:
                    # Current season generic
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['current_param']}"
                else:
                    # Historical season
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['url_base']}_{year}"
                
                self.stdout.write(f"Scraping {year}: {url}")

                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code != 200:
                         self.stdout.write(self.style.ERROR(f"Failed {url}: {response.status_code}"))
                         continue

                    # Parse HTML tables
                    # SoccerStats tables are often nested. We look for the one with proper headers.
                    # Expected cols: Date, Home, Score, Away...
                    
                    dfs = pd.read_html(StringIO(response.text))
                    
                    target_df = None
                    for df in dfs:
                        # Clean cols
                        cols = [str(c).lower() for c in df.columns]
                        # Check for presence of score-like columns or team names
                        # SoccerStats often has no clear headers in the `read_html` output because they use complex headers.
                        # But the data rows usually look like: [Date] [Home] [Score] [Away] ...
                        
                        # Heuristic: verify if column 0 looks like a date or has many rows
                        # Brazil 2026 might have fewer rows if just started
                        if len(df) > 10: 
                             # Check if it has team names roughly
                             sample_row = df.iloc[0].astype(str).str.cat()
                             if ' - ' in sample_row or '-' in sample_row or '–' in sample_row:
                                 target_df = df
                                 break # Found a likely match table

                    if target_df is None and dfs:
                        # Fallback to largest table if specific pattern not found
                        target_df = max(dfs, key=len)

                    if target_df is not None:
                        # Save CSV
                        filename = f"{base_dir}/{league_conf['name'].lower()}_{year}.csv"
                        target_df.to_csv(filename, index=False, encoding='utf-8')
                        self.stdout.write(self.style.SUCCESS(f"Saved CSV: {filename}"))
                        
                        if not csv_only:
                            self.process_table(target_df, league_obj, year)
                    else:
                        self.stdout.write(self.style.WARNING("No suitable data table found."))
                    
                    # Sleep to avoid block
                    sleep_sec = random.uniform(3, 6)
                    self.stdout.write(f"Sleeping {sleep_sec:.1f}s...")
                    time.sleep(sleep_sec)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error {year}: {e}"))
                    
    def process_table(self, df, league_obj, year):
        # Provide logic to parse the specific SoccerStats visual table
        # It usually has: Date | Home | Score | Away | ...
        # But pandas read_html might interpret headers poorly.
        
        # We iterate rows and try to identify match patterns.
        count = 0
        
        season_obj, _ = Season.objects.get_or_create(year=year)
        
        for idx, row in df.iterrows():
            try:
                # SoccerStats structure varies.
                # Often: Col 0 (Date), Col 1 (Home), Col 2 (Score), Col 3 (Away)
                # But sometimes there are hidden columns.
                
                # Let's try to grab by index if columns are unnamed
                # Convert row to list
                vals = [str(x).strip() for x in row.values]
                
                if len(vals) < 4: continue
                
                # Score val is at index 2
                score_val = vals[2]

                date_raw = vals[0]
                home = vals[1]
                away = vals[3]
                
                if not home or not away or home == 'nan' or away == 'nan': continue
                
                # Standardize Team Names for Brazil
                # SoccerStats might use different names. We map them to our DB names.
                team_mapping = {
                    'Corinthians': 'Corinthians',
                    'Sport Club Corinthians Paulista': 'Corinthians',
                    'SC Corinthians Paulista': 'Corinthians',
                    'Athletico Paranaense': 'CA Paranaense',
                    'Athletico-PR': 'CA Paranaense',
                    'Athletico PR': 'CA Paranaense',
                    'Atletico PR': 'CA Paranaense',
                    'Atlético Mineiro': 'CA Mineiro',
                    'Atletico-MG': 'CA Mineiro',
                    'Atletico MG': 'CA Mineiro',
                    'Atlético-MG': 'CA Mineiro',
                    'Botafogo RJ': 'Botafogo',
                    'Botafogo FR': 'Botafogo',
                    'Bragantino': 'RB Bragantino',
                    'Red Bull Bragantino': 'RB Bragantino',
                    'Chapecoense': 'Chapecoense AF',
                    'Chapecoense-SC': 'Chapecoense AF',
                    'Coritiba': 'Coritiba FBC',
                    'Flamengo': 'Flamengo',
                    'Flamengo RJ': 'Flamengo',
                    'CR Flamengo': 'Flamengo',
                    'Vasco da Gama': 'Vasco',
                    'Vasco': 'Vasco',
                    'CR Vasco da Gama': 'Vasco',
                    'Vitoria': 'Vitoria',
                    'EC Vitória': 'Vitoria',
                    'Vitoria BA': 'Vitoria',
                    'Internacional': 'Internacional',
                    'SC Internacional': 'Internacional',
                    'Fluminense': 'Fluminense',
                    'Fluminense FC': 'Fluminense',
                    'Sao Paulo': 'Sao Paulo',
                    'São Paulo': 'Sao Paulo',
                    'São Paulo FC': 'Sao Paulo',
                    'Cruzeiro': 'Cruzeiro',
                    'Cruzeiro EC': 'Cruzeiro',
                    'Mirassol': 'Mirassol FC',
                    'Remo': 'Clube do Remo',
                    'Palmeiras': 'Palmeiras',
                    'SE Palmeiras': 'Palmeiras',
                    'Goias': 'Goias',
                    'Goias EC': 'Goias',
                    'Cuiaba': 'Cuiaba',
                    'Cuiaba EC': 'Cuiaba',
                    'Fortaleza': 'Fortaleza',
                    'Fortaleza EC': 'Fortaleza',
                    'America MG': 'America MG',
                    'America-MG': 'America MG',
                    'Atletico GO': 'Atletico GO',
                    'Atletico-GO': 'Atletico GO',
                    'Juventude': 'Juventude',
                    'EC Juventude': 'Juventude',
                }
                
                home = team_mapping.get(home, home)
                away = team_mapping.get(away, away)
                
                # Check if it looks like a match row
                # Score usually "1 - 0", "1:0" or "2-2"
                score_val = score_val.replace('–', '-').replace(':', '-')
                
                if '-' not in score_val:
                    # Maybe it's a date or time (scheduled)
                    h_score = None
                    a_score = None
                    status = 'Scheduled'
                else:
                    # Parse Score
                    try:
                        parts = score_val.split('-')
                        h_score = int(parts[0])
                        a_score = int(parts[1])
                        status = 'Finished'
                    except:
                        # Might be postponed or invalid (e.g. "pp.")
                        h_score = None
                        a_score = None
                        status = 'Scheduled'

                # Date
                # SoccerStats date is usually "Sat 12 Aug". Needs Year appended.
                # We know the 'year' argument.
                # Be careful with spanning seasons (Premier League). Aug-Dec is year-1, Jan-May is year.
                
                match_date = None
                try:
                    # Parse "Sat 29 Jan" -> datetime
                    # If date_raw has no year, append 'year'
                    if len(date_raw) > 3:
                         # Attempt parse: "Sat 29 Jan"
                         # Python strptime '%a %d %b'
                         # We need to handle portuguese/english? SoccerStats is usually English.
                         # But let's check content.
                         pass
                except:
                    pass
                
                home_team, _ = Team.objects.get_or_create(name=home, league=league_obj)
                away_team, _ = Team.objects.get_or_create(name=away, league=league_obj)

                Match.objects.update_or_create(
                    league=league_obj,
                    season=season_obj,
                    home_team=home_team,
                    away_team=away_team,
                    defaults={
                        'home_score': h_score,
                        'away_score': a_score,
                        'status': status
                        # Date logic omitted for safety in this rough draft, can add if easy
                    }
                )
                count += 1
                
            except Exception:
                continue
        
        self.stdout.write(self.style.SUCCESS(f"Saved/Updated {count} matches for {year}"))
