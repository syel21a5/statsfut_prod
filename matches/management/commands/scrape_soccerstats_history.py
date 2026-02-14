
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
                
                if year == 2025:
                    # Current season - use base URL
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
                        if len(df) > 50: # A league season has 380 games
                             target_df = df
                             # Just taking the largest is often safest in simple scraper
                             break
                    
                    if target_df is None and dfs:
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
                
                # Check if it looks like a match row
                # Score usually "1 - 0" or "2-2"
                score_val = vals[2]
                if '-' not in score_val and '–' not in score_val:
                    # Maybe shifted?
                    # Let's try to find the score column dynamically?
                    continue

                date_raw = vals[0]
                home = vals[1]
                away = vals[3]
                
                if not home or not away or home == 'nan' or away == 'nan': continue
                
                # Parse Score
                score_clean = score_val.replace('–', '-')
                try:
                    parts = score_clean.split('-')
                    h_score = int(parts[0])
                    a_score = int(parts[1])
                    status = 'Finished'
                except:
                    # Might be postponed or invalid
                    h_score = None
                    a_score = None
                    status = 'Scheduled'

                # Date
                # SoccerStats date is usually "Sat 12 Aug". Needs Year appended.
                # We know the 'year' argument.
                # Be careful with spanning seasons (Premier League). Aug-Dec is year-1, Jan-May is year.
                
                match_date = None
                try:
                    # This is tricky without strict parsing logic. 
                    # For now, we will save it. Improvements can be made to accurate date parsing.
                    # Simple heuristic:
                    pass
                except:
                    pass
                
                Match.objects.update_or_create(
                    league=league_obj,
                    season=season_obj,
                    home_team=Team.objects.get_or_create(name=home, league=league_obj)[0],
                    away_team=Team.objects.get_or_create(name=away, league=league_obj)[0],
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
