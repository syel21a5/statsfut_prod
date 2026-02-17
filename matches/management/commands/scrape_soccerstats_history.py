
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
        parser.add_argument('--target_league', type=str, help='Process only a specific league by name (e.g. \"A League\")')

    def handle(self, *args, **kwargs):
        years = kwargs['years'] or list(range(2016, 2027))
        csv_only = kwargs['csv_only']
        target_league = kwargs.get('target_league')
        
        # Ensure export directory exists
        base_dir = "csv_exports"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        leagues = [
            {
                'name': 'Premier League',
                'country': 'Inglaterra',
                'url_base': 'england',
                'current_param': 'england'
            },
            {
                'name': 'Brasileirão',
                'country': 'Brasil',
                'url_base': 'brazil',
                'current_param': 'brazil'
            },
            {
                'name': 'Pro League',
                'country': 'Belgica',
                'url_base': 'belgium',
                'current_param': 'belgium'
            },
            {
                'name': 'A League',
                'country': 'Australia',
                'url_base': 'australia',
                'current_param': 'australia'
            },
            {
                'name': 'First League',
                'country': 'Republica Tcheca',
                'url_base': 'czechrepublic',
                'current_param': 'czechrepublic'
            }
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        for league_conf in leagues:
            if target_league and league_conf['name'] != target_league:
                continue

            self.stdout.write(self.style.SUCCESS(f"--- Processing {league_conf['name']} ---"))
            
            league_obj = None
            if not csv_only:
                league_obj, _ = League.objects.get_or_create(
                    name=league_conf['name'], 
                    country=league_conf['country']
                )

            for year in years:
                if league_conf['name'] == 'First League':
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['current_param']}"
                elif (league_conf['name'] == 'Brasileirão' and year == 2026) or \
                     (league_conf['name'] == 'Pro League' and year == 2026):
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['current_param']}"
                elif year == 2025:
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['current_param']}"
                else:
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['url_base']}_{year}"
                
                self.stdout.write(f"Scraping {year}: {url}")

                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code != 200:
                         self.stdout.write(self.style.ERROR(f"Failed {url}: {response.status_code}"))
                         # Still try subpages if it's a recent year

                    urls_to_try = [url]
                    if league_conf['name'] == 'Brasileirão' and year >= 2025:
                        for m in range(1, 6):
                            urls_to_try.append(f"{url}&tid=m{m}")
                    elif league_conf['name'] == 'First League' and year == 2026:
                        for m in range(1, 13):
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
                vals = [str(x).strip() for x in row.values]
                
                if len(vals) < 4: continue
                
                score_val = vals[2]
                raw_score_val = score_val

                date_raw = vals[0]
                home = vals[1]
                away = vals[3]
                
                if not home or not away or home == 'nan' or away == 'nan': continue
                
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
                    
                    # Belgium Mappings
                    'Union SG': 'Royale Union SG',
                    'Royale Union SG': 'Royale Union SG',
                    'Sint-Truiden': 'Sint-Truiden',
                    'STVV': 'Sint-Truiden',
                    'Club Brugge': 'Club Brugge',
                    'Club Brugge KV': 'Club Brugge',
                    'KAA Gent': 'Gent',
                    'Gent': 'Gent',
                    'KV Mechelen': 'Mechelen',
                    'Mechelen': 'Mechelen',
                    'KRC Genk': 'Genk',
                    'Genk': 'Genk',
                    'RSC Anderlecht': 'Anderlecht',
                    'Anderlecht': 'Anderlecht',
                    'Sporting Charleroi': 'Charleroi',
                    'Charleroi': 'Charleroi',
                    'KVC Westerlo': 'Westerlo',
                    'Westerlo': 'Westerlo',
                    'Royal Antwerp FC': 'Antwerp',
                    'Antwerp': 'Antwerp',
                    'Zulte Waregem': 'Zulte-Waregem',
                    'Zulte-Waregem': 'Zulte-Waregem',
                    'Standard Liège': 'Standard Liege',
                    'Standard Liege': 'Standard Liege',
                    'OH Leuven': 'OH Leuven',
                    'Oud-Heverlee Leuven': 'OH Leuven',
                    'Cercle Brugge': 'Cercle Brugge',
                    'Cercle Brugge KSV': 'Cercle Brugge',
                    'FCV Dender EH': 'Dender',
                    'Dender': 'Dender',
                    'Beerschot': 'Beerschot',
                    'KV Kortrijk': 'Kortrijk',
                    'Kortrijk': 'Kortrijk',
                }
                
                home = team_mapping.get(home, home)
                away = team_mapping.get(away, away)
                
                # Hard guards: skip obvious non-team rows
                blacklist_tokens = {
                    'averages','percentages','copyright','privacy','contact','matches',
                    'defence','offence','home','away','fav','apr','feb','jan','mar',
                    'segment','points','played','goals','from','to','pts','team'
                }
                def is_garbage(name):
                    n = (name or '').strip().lower()
                    if not n: return True
                    if any(tok == n or tok in n for tok in blacklist_tokens): return True
                    if any(ch.isdigit() for ch in n): return True
                    if '%' in n: return True
                    return False
                
                if is_garbage(home) or is_garbage(away):
                    continue
                
                is_finished = False
                ht_val = vals[5] if len(vals) > 5 else ""
                if '(' in ht_val and ')' in ht_val:
                    is_finished = True
                elif '-' in score_val and not (len(score_val) == 5 and score_val[2] == ':'): # Not HH:MM
                     # Fallback check
                     is_finished = True

                score_val = score_val.replace('–', '-').replace(':', '-')
                
                if '-' in score_val and is_finished:
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
                else:
                    # Treat as scheduled only if looks like a time and we can parse date later
                    if ':' in raw_score_val:
                        h_score = None
                        a_score = None
                        status = 'Scheduled'
                    else:
                        # Not a match row
                        continue

                match_date = None
                try:
                    parts = date_raw.split()
                    if len(parts) >= 3:
                        date_str = " ".join(parts[:3])
                        base_dt = datetime.strptime(date_str, "%a %d %b")
                        month = base_dt.month
                        day = base_dt.day
                        if league_obj.name == 'Brasileirão':
                            year_val = year
                        else:
                            year_val = year - 1 if month >= 8 else year
                        naive_dt = datetime(year_val, month, day)
                        match_date = timezone.make_aware(naive_dt, pytz.UTC)
                        if status == 'Scheduled' and ':' in raw_score_val:
                            try:
                                hour, minute = map(int, raw_score_val.split(':'))
                                match_date = match_date.replace(hour=hour, minute=minute)
                            except Exception:
                                pass
                except:
                    pass
                
                home_team, _ = Team.objects.get_or_create(name=home, league=league_obj)
                away_team, _ = Team.objects.get_or_create(name=away, league=league_obj)

                if home_team == away_team:
                    continue

                defaults = {
                    'home_score': h_score,
                    'away_score': a_score,
                    'status': status
                }
                if match_date:
                    defaults['date'] = match_date

                Match.objects.update_or_create(
                    league=league_obj,
                    season=season_obj,
                    home_team=home_team,
                    away_team=away_team,
                    defaults=defaults
                )
                count += 1
                
            except Exception:
                continue
        
        self.stdout.write(self.style.SUCCESS(f"Saved/Updated {count} matches for {year}"))
