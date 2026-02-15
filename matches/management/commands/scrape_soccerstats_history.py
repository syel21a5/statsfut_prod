
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
                         # Still try subpages if it's a recent year

                    # For the current year, let's try to fetch by month to get everything
                    # Monthly subpages: tid=m1, tid=m2, etc. (1-12)
                    # We'll try common active months for Brazil (Jan to May if it's early year)
                    urls_to_try = [url]
                    if year >= 2025: # Recent or current
                        for m in range(1, 6): # Try Jan to May
                            urls_to_try.append(f"{url}&tid=m{m}")
                    
                    for attempt_url in urls_to_try:
                        try:
                            self.stdout.write(f"Scraping: {attempt_url}")
                            resp = requests.get(attempt_url, headers=headers)
                            if resp.status_code != 200: continue
                            
                            dfs_list = pd.read_html(StringIO(resp.text))
                            for df_item in dfs_list:
                                if df_item.shape[1] >= 4:
                                    self.process_table(df_item, league_obj, year)
                            
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Failed to scrape month subpage {attempt_url}: {e}"))

                    # End of year processing
                    sleep_sec = random.uniform(2, 4)
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
        
        if df.shape[1] < 4: return # Ensure it has enough columns to be a match table
        
        # This is likely a results table
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
                    'CA Paranaense': 'CA Paranaense',
                    'Atletico MG': 'CA Mineiro',
                    'Atletico-MG': 'CA Mineiro',
                    'Atlético Mineiro': 'CA Mineiro',
                    'Atlético-MG': 'CA Mineiro',
                    'CA Mineiro': 'CA Mineiro',
                    'Bragantino': 'RB Bragantino',
                    'Red Bull Bragantino': 'RB Bragantino',
                    'RB Bragantino': 'RB Bragantino',
                    'SC Corinthians Paulista': 'Corinthians',
                    'Sport Club Corinthians Paulista': 'Corinthians',
                    'Corinthians': 'Corinthians',
                    'Flamengo RJ': 'Flamengo',
                    'CR Flamengo': 'Flamengo',
                    'Flamengo': 'Flamengo',
                    'Vasco da Gama': 'Vasco',
                    'CR Vasco da Gama': 'Vasco',
                    'Vasco': 'Vasco',
                    'EC Vitória': 'Vitoria',
                    'Vitoria BA': 'Vitoria',
                    'Vitoria': 'Vitoria',
                    'Chapecoense': 'Chapecoense AF',
                    'Chapecoense-SC': 'Chapecoense AF',
                    'Chapecoense AF': 'Chapecoense AF',
                    'Coritiba': 'Coritiba FBC',
                    'Coritiba FBC': 'Coritiba FBC',
                    'SC Internacional': 'Internacional',
                    'Internacional': 'Internacional',
                    'Fluminense FC': 'Fluminense',
                    'Fluminense': 'Fluminense',
                    'São Paulo': 'Sao Paulo',
                    'São Paulo FC': 'Sao Paulo',
                    'Sao Paulo': 'Sao Paulo',
                    'Cruzeiro EC': 'Cruzeiro',
                    'Cruzeiro': 'Cruzeiro',
                    'Mirassol': 'Mirassol FC',
                    'Mirassol FC': 'Mirassol FC',
                    'Remo': 'Clube do Remo',
                    'Clube do Remo': 'Clube do Remo',
                    'SE Palmeiras': 'Palmeiras',
                    'Palmeiras': 'Palmeiras',
                    'Goias EC': 'Goias',
                    'Goias': 'Goias',
                    'Cuiaba EC': 'Cuiaba',
                    'Cuiaba': 'Cuiaba',
                    'Fortaleza EC': 'Fortaleza',
                    'Fortaleza': 'Fortaleza',
                    'America-MG': 'America MG',
                    'America MG': 'America MG',
                    'Atletico-GO': 'Atletico GO',
                    'Atletico GO': 'Atletico GO',
                    'EC Juventude': 'Juventude',
                    'Juventude': 'Juventude',
                    'Grêmio FBPA': 'Gremio',
                    'Gremio': 'Gremio',
                }
                
                home = team_mapping.get(home, home)
                away = team_mapping.get(away, away)
                
                # Check if it looks like a match row
                # Score usually "1 - 0", "1:0" or "2-2"
                # If it's a time (e.g. 00:30), it's Scheduled.
                
                # Dynamic column check: vals[5] is usually HT score "(1-0)" for finished games
                is_finished = False
                ht_val = vals[5] if len(vals) > 5 else ""
                if '(' in ht_val and ')' in ht_val:
                    is_finished = True
                elif '-' in score_val and not (len(score_val) == 5 and score_val[2] == ':'): # Not HH:MM
                     # Fallback check
                     is_finished = True

                score_val = score_val.replace('–', '-').replace(':', '-')
                
                if '-' not in score_val or not is_finished:
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
