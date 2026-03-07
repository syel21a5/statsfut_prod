
import os
import time
import sys
import random
import requests
import pandas as pd
from io import StringIO
from datetime import datetime
import pytz
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League, Team, Match, Season
from django.utils import timezone
from matches.utils_odds_api import ODDS_API_TEAM_MAPPINGS

class Command(BaseCommand):
    help = 'Scrape historical match results from SoccerStats.com'

    def add_arguments(self, parser):
        parser.add_argument('--years', nargs='+', type=int, help='Years to scrape (e.g. 2024 for 2023/24)')
        parser.add_argument('--csv_only', action='store_true', help='Save to CSV only, do not import to DB')
        parser.add_argument('--target_league', type=str, help='Process only a specific league by name (e.g. \"A League\")')
        parser.add_argument('--target_slug', type=str, help='Process only a specific league by SoccerStats slug (e.g. czechrepublic)')
        parser.add_argument('--team_url', type=str, help='Import matches from a SoccerStats team page (teamstats.asp)')

    def handle(self, *args, **kwargs):
        years = kwargs['years'] or list(range(2016, 2027))
        csv_only = kwargs['csv_only']
        target_league = kwargs.get('target_league')
        target_slug = (kwargs.get('target_slug') or '').strip().lower() or None
        team_url = (kwargs.get('team_url') or '').strip()
        
        self.processed_matches = set()
        
        self.stdout.write(f"DEBUG: Scraper started. target_slug={target_slug}, years={years}")
        sys.stdout.flush()

        # Ensure export directory exists
        base_dir = "csv_exports"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # If a team_url is provided, run one-off import from that page and exit early
        if team_url:
            try:
                self.stdout.write(self.style.SUCCESS(f"Importing team page: {team_url}"))
                self.import_from_team_page(team_url, csv_only)
                self.stdout.write(self.style.SUCCESS("Team page import completed"))
                return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to import team page: {e}"))
                return

        leagues = [
            {
                'name': 'Premier League',
                'country': 'Inglaterra',
                'division': 1,
                'url_base': 'england',
                'current_param': 'england'
            },
            {
                'name': 'Brasileirão',
                'country': 'Brasil',
                'division': 1,
                'url_base': 'brazil',
                'current_param': 'brazil'
            },
            {
                'name': 'Pro League',
                'country': 'Belgica',
                'division': 1,
                'url_base': 'belgium',
                'current_param': 'belgium'
            },
            {
                'name': 'A League',
                'country': 'Australia',
                'division': 1,
                'url_base': 'australia',
                'current_param': 'australia'
            },
            {
                'name': 'First League',
                'country': 'Republica Tcheca',
                'division': 1,
                'url_base': 'czechrepublic',
                'current_param': 'czechrepublic'
            },
            {
                'name': 'Bundesliga',
                'country': 'Austria',
                'division': 1,
                'url_base': 'austria',
                'current_param': 'austria'
            },
            {
                'name': 'Super League',
                'country': 'Suica',
                'division': 1,
                'url_base': 'switzerland',
                'current_param': 'switzerland'
            },
            {
                'name': 'Superliga',
                'country': 'Dinamarca',
                'division': 1,
                'url_base': 'denmark',
                'current_param': 'denmark'
            }
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        for league_conf in leagues:
            self.stdout.write(f"DEBUG: Checking {league_conf['name']} ({league_conf.get('current_param')})")
            sys.stdout.flush()
            if target_league and league_conf['name'] != target_league:
                continue
            if target_slug:
                if (league_conf.get('current_param','').lower() != target_slug) and (league_conf.get('url_base','').lower() != target_slug):
                    self.stdout.write(f"DEBUG: Skipping {league_conf['name']} (slug mismatch)")
                    sys.stdout.flush()
                    continue
            
            self.stdout.write(f"DEBUG: Processing {league_conf['name']} matched!")
            sys.stdout.flush()

            self.stdout.write(self.style.SUCCESS(f"--- Processing {league_conf['name']} ---"))
            sys.stdout.flush()
            
            league_obj = None
            if not csv_only:
                self.stdout.write(f"DEBUG: Getting League object for {league_conf['name']}...")
                sys.stdout.flush()
                try:
                    slug = league_conf.get('url_base')
                    league_obj = None
                    if slug:
                        league_obj = League.objects.filter(soccerstats_slug=slug).first()
                    if not league_obj:
                        league_obj, _ = League.objects.get_or_create(
                            name=league_conf['name'],
                            country=league_conf['country'],
                            division=league_conf.get('division', 1),
                        )
                    # Persist the soccerstats slug so it's always up to date
                    if slug and league_obj.soccerstats_slug != slug:
                        league_obj.soccerstats_slug = slug
                        league_obj.save(update_fields=['soccerstats_slug'])
                    self.stdout.write(f"DEBUG: League object retrieved: {league_obj}")
                    sys.stdout.flush()
                except Exception as e:
                    self.stdout.write(f"ERROR: DB Error: {e}")
                    sys.stdout.flush()
                    continue

            for year in years:
                if league_conf['name'] == 'First League':
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['current_param']}&pmtype=bydate"
                elif (league_conf['name'] == 'Brasileirão' and year == 2026):
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['current_param']}"
                elif (league_conf['name'] == 'Pro League' and year == 2026) or \
                     (league_conf['name'] == 'Super League' and year == 2026) or \
                     (league_conf['name'] == 'Superliga' and year == 2026) or \
                     (league_conf['name'] == 'Bundesliga' and league_conf['country'] == 'Austria' and year == 2026) or \
                     (league_conf['name'] == 'A League' and year == 2026):
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['current_param']}&pmtype=bydate"
                else:
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['url_base']}_{year}"
                
                self.stdout.write(f"Scraping {year}: {url}")

                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code != 200:
                         self.stdout.write(self.style.ERROR(f"Failed {url}: {response.status_code}. Trying alternative URL..."))
                         # Alternative URL for older seasons that don't use _year suffix
                         url = f"https://www.soccerstats.com/results.asp?league={league_conf['url_base']}&pmtype=bydate"
                         self.stdout.write(f"Scraping {year} (alternative): {url}")
                         response = requests.get(url, headers=headers, timeout=15)
                         if response.status_code != 200:
                            self.stdout.write(self.style.ERROR(f"Alternative URL also failed: {response.status_code}"))
                            continue

                    urls_to_try = [url]
                    if league_conf['name'] == 'Brasileirão' and year >= 2025:
                        for m in range(1, 6):
                            urls_to_try.append(f"{url}&tid=m{m}")
                    
                    # Pre-fetch main page content for duplicate checking if we have multiple URLs
                    main_page_content_len = 0
                    if len(urls_to_try) > 1:
                         try:
                             # We use the first URL (main year URL) as baseline
                             if urls_to_try[0] != url: # ensure we don't fetch if not needed, but here url is base
                                 pass
                             main_resp = requests.get(urls_to_try[0], headers=headers, timeout=15)
                             main_page_content_len = len(main_resp.text)
                         except:
                             pass

                    processed_urls = set()

                    for attempt_url in urls_to_try:
                        if attempt_url in processed_urls: continue
                        processed_urls.add(attempt_url)

                        try:
                            self.stdout.write(f"Scraping: {attempt_url}")
                            resp = requests.get(attempt_url, headers=headers)
                            if resp.status_code != 200: continue
                            
                            # Check if redirected to main page or content is identical to main page
                            # A tolerance of small bytes difference might be needed due to dynamic timestamps/ads
                            if main_page_content_len > 0 and abs(len(resp.text) - main_page_content_len) < 1000 and attempt_url != urls_to_try[0]:
                                self.stdout.write(f"DEBUG: Skipping {attempt_url} (seems duplicate of main page)")
                                continue

                            dfs_list = pd.read_html(StringIO(resp.text))
                            for df_item in dfs_list:
                                if df_item.shape[1] >= 4:
                                    self.process_table(df_item, league_obj, year)
                            
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Failed to scrape month subpage {attempt_url}: {e}"))

                    # End of year processing
                    sleep_sec = random.uniform(2, 4)
                    time.sleep(sleep_sec)

                    # Automatically recalculate standings for this league/year
                    # This ensures we use the exact same league object we just scraped for
                    try:
                        self.stdout.write(self.style.SUCCESS(f"Auto-recalculating standings for {league_obj.name} ({league_obj.country}) - {year}"))
                        call_command('recalculate_standings', league_name=league_obj.name, country=league_obj.country, season_year=year)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Failed to auto-recalculate standings: {e}"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error {year}: {e}"))
                    
    def process_table(self, df, league_obj, year):
        # Provide logic to parse the specific SoccerStats visual table
        # It usually has: Date | Home | Score | Away | ...
        # But pandas read_html might interpret headers poorly.
        
        # We iterate rows and try to identify match patterns.
        count = 0
        
        def get_team(name, league):
            from django.utils.text import slugify
            try:
                # 1. Exact match
                return Team.objects.get(name__iexact=name, league=league)
            except Team.DoesNotExist:
                # 2. Slug match (robust against SK Sturm Graz vs Sturm Graz)
                target_slug = slugify(name)
                for t in Team.objects.filter(league=league):
                    if slugify(t.name) == target_slug:
                        return t
                
                # 3. Contains match
                t = Team.objects.filter(league=league, name__icontains=name).first()
                if t:
                    return t
                
                # 4. Create new
                t, _ = Team.objects.get_or_create(name=name, league=league)
                return t
        
        season_obj, _ = Season.objects.get_or_create(year=year)
        
        if df.shape[1] < 3: return
        
        for idx, row in df.iterrows():
            try:
                vals = [str(x).strip() for x in row.values.tolist()]
                
                if len(vals) < 3: 
                    continue
                
                score_idx = None
                for i, v in enumerate(vals):
                    vv = v.replace('–', '-').replace('—', '-').replace('−', '-')
                    if vv and ((':' in vv) or ('-' in vv)):
                        p = vv.replace(' ', '')
                        if ':' in p:
                            parts = p.split(':')
                        else:
                            parts = p.split('-')
                        if len(parts) == 2 and all(part.isdigit() for part in parts):
                            score_idx = i
                            break
                if score_idx is None:
                    continue
                raw_score_val = vals[score_idx]
                score_val = raw_score_val

                home = None
                for i in range(score_idx - 1, -1, -1):
                    candidate = vals[i]
                    if candidate and candidate.lower() not in {'vs', 'v'}:
                        home = candidate
                        break
                away = None
                for i in range(score_idx + 1, len(vals)):
                    candidate = vals[i]
                    if candidate:
                        away = candidate
                        break
                
                date_raw = None
                for i in range(0, score_idx):
                    candidate = vals[i]
                    if len(candidate.split()) >= 3:
                        date_raw = candidate
                        break
                
                if not home or not away or home == 'nan' or away == 'nan': continue
                
                team_mapping = {
                    # Brazil mappings -> Nomes canônicos usados no banco
                    'Corinthians': 'Corinthians',
                    'Sport Club Corinthians Paulista': 'Corinthians',
                    'SC Corinthians Paulista': 'Corinthians',
                    'Athletico Paranaense': 'Athletico-PR',
                    'Athletico-PR': 'Athletico-PR',
                    'Athletico PR': 'Athletico-PR',
                    'Atletico PR': 'Athletico-PR',
                    'CA Paranaense': 'Athletico-PR',
                    'Atlético Mineiro': 'Atletico-MG',
                    'Atletico-MG': 'Atletico-MG',
                    'Atletico MG': 'Atletico-MG',
                    'Atlético-MG': 'Atletico-MG',
                    'CA Mineiro': 'Atletico-MG',
                    'Bragantino': 'Bragantino',
                    'Red Bull Bragantino': 'Bragantino',
                    'RB Bragantino': 'Bragantino',
                    'Flamengo RJ': 'Flamengo',
                    'CR Flamengo': 'Flamengo',
                    'Flamengo': 'Flamengo',
                    'Vasco da Gama': 'Vasco',
                    'CR Vasco da Gama': 'Vasco',
                    'Vasco': 'Vasco',
                    'EC Vitória': 'Vitoria',
                    'Vitoria BA': 'Vitoria',
                    'Vitoria': 'Vitoria',
                    'Chapecoense': 'Chapecoense',
                    'Chapecoense-SC': 'Chapecoense',
                    'Chapecoense AF': 'Chapecoense',
                    'Coritiba': 'Coritiba',
                    'Coritiba FBC': 'Coritiba',
                    'SC Internacional': 'Internacional',
                    'Internacional': 'Internacional',
                    'Fluminense FC': 'Fluminense',
                    'Fluminense': 'Fluminense',
                    'São Paulo': 'Sao Paulo',
                    'São Paulo FC': 'Sao Paulo',
                    'Sao Paulo': 'Sao Paulo',
                    'Cruzeiro EC': 'Cruzeiro',
                    'Cruzeiro': 'Cruzeiro',
                    'Mirassol': 'Mirassol',
                    'Mirassol FC': 'Mirassol',
                    'Remo': 'Remo',
                    'Clube do Remo': 'Remo',
                    'SE Palmeiras': 'Palmeiras',
                    'Palmeiras': 'Palmeiras',
                    'Goias EC': 'Goias',
                    'Goias': 'Goias',
                    'Cuiaba EC': 'Cuiaba',
                    'Cuiaba': 'Cuiaba',
                    'Fortaleza EC': 'Fortaleza',
                    'Fortaleza': 'Fortaleza',
                    'America-MG': 'America-MG',
                    'America MG': 'America-MG',
                    'Atletico-GO': 'Atletico-GO',
                    'Atletico GO': 'Atletico-GO',
                    'EC Juventude': 'Juventude',
                    'Juventude': 'Juventude',
                    'Grêmio FBPA': 'Gremio',
                    'Gremio': 'Gremio',
                    
                    # Belgium mappings
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

                    # Austria mappings
                    'Red Bull Salzburg': 'Salzburg',
                    'RB Salzburg': 'Salzburg',
                    'Salzburg': 'Salzburg',
                    'Sturm Graz': 'Sturm Graz',
                    'SK Sturm Graz': 'Sturm Graz',
                    'LASK': 'LASK Linz',
                    'LASK Linz': 'LASK Linz',
                    'Rapid Wien': 'Rapid Wien',
                    'Rapid Vienna': 'Rapid Wien',
                    'Austria Wien': 'Austria Wien',
                    'Austria Vienna': 'Austria Wien',
                    'Wolfsberger AC': 'Wolfsberger AC',
                    'WAC': 'Wolfsberger AC',
                    'SK Austria Klagenfurt': 'Austria Klagenfurt',
                    'A. Klagenfurt': 'Austria Klagenfurt',
                    'Austria Klagenfurt': 'Austria Klagenfurt',
                    'TSV Hartberg': 'Hartberg',
                    'Hartberg': 'Hartberg',
                    'SCR Altach': 'Altach',
                     'Altach': 'Altach',
                    'FC Blau Weiss Linz': 'BW Linz',
                    'BW Linz': 'BW Linz',
                    'Blau-Weiss Linz': 'BW Linz',
                    'WSG Tirol': 'Tirol',
                    'Tirol': 'Tirol',
                    'Grazer AK': 'Grazer AK',
                    'GAK': 'Grazer AK',
                    'Austria Lustenau': 'Austria Lustenau',
                    'A. Lustenau': 'Austria Lustenau',
                    'SCR Ried': 'Ried',
                    'SV Ried': 'Ried',
                    'Ried': 'Ried',

                    # Add SK/SC prefixes to match production database if needed
                    'Salzburg': 'Red Bull Salzburg',
                    'Sturm Graz': 'SK Sturm Graz',
                    'Rapid Wien': 'SK Rapid Wien',
                    'Austria Wien': 'FK Austria Wien',
                    'Klagenfurt': 'SK Austria Klagenfurt',

                    # Switzerland mappings
                    'Young Boys': 'Young Boys',
                    'BSC Young Boys': 'Young Boys',
                    'Lugano': 'Lugano',
                    'FC Lugano': 'Lugano',
                    'Servette': 'Servette',
                    'Servette FC': 'Servette',
                    'Zurich': 'Zurich',
                    'FC Zurich': 'Zurich',
                    'FC Zürich': 'Zurich',
                    'St. Gallen': 'St. Gallen',
                    'FC St. Gallen': 'St. Gallen',
                    'FC St Gallen': 'St. Gallen',
                    'Luzern': 'Luzern',
                    'FC Luzern': 'Luzern',
                    'Basel': 'Basel',
                    'FC Basel': 'Basel',
                    'Winterthur': 'Winterthur',
                    'FC Winterthur': 'Winterthur',
                    'Yverdon': 'Yverdon',
                    'Yverdon-Sport FC': 'Yverdon',
                    'Yverdon Sport': 'Yverdon',
                    'Lausanne': 'Lausanne',
                    'FC Lausanne-Sport': 'Lausanne',
                    'Lausanne-Sport': 'Lausanne',
                    'Lausanne Sport': 'Lausanne',
                    'Grasshoppers': 'Grasshoppers',
                    'Grasshopper Club Zurich': 'Grasshoppers',
                    'Grasshopper': 'Grasshoppers',
                    'Sion': 'Sion',
                    'FC Sion': 'Sion',
                    'Thun': 'Thun',
                    'FC Thun': 'Thun',
                    'Stade Lausanne-Ouchy': 'Lausanne Ouchy',
                    'Lausanne Ouchy': 'Lausanne Ouchy',
                    'FC Vaduz': 'Vaduz',
                    'Vaduz': 'Vaduz',
                    'Neuchatel Xamax': 'Neuchatel Xamax',
                    'Neuchâtel Xamax': 'Neuchatel Xamax',
                    'Xamax': 'Neuchatel Xamax',
                    'FC Aarau': 'Aarau',
                    'Aarau': 'Aarau',

                    # Australia mappings
                    'Wellington': 'Wellington Phoenix FC',
                    'Wellington Phoenix FC': 'Wellington Phoenix FC',
                    'Wellington Phoenix': 'Wellington Phoenix FC',
                    'Melbourne V.': 'Melbourne Victory',
                    'Melbourne Victory FC': 'Melbourne Victory',
                    'Adelaide Utd': 'Adelaide United',
                    'Adelaide United FC': 'Adelaide United',
                    'Central Coast': 'Central Coast Mariners',
                    'Central Coast Mariners FC': 'Central Coast Mariners',
                    'Macarthur FC': 'Macarthur FC',
                    'Macarthur': 'Macarthur FC',
                    'Western United': 'Western United',
                    'Western United FC': 'Western United',
                    'Western Utd': 'Western United',
                    'WS Wanderers': 'Western Sydney Wanderers',
                    'Western Sydney': 'Western Sydney Wanderers',
                    'WSW': 'Western Sydney Wanderers',
                    'Newcastle Jets': 'Newcastle Jets FC',
                    'Newcastle Jets FC': 'Newcastle Jets FC',
                    'Brisbane Roar': 'Brisbane Roar',
                    'Brisbane Roar FC': 'Brisbane Roar',
                    'Perth Glory': 'Perth Glory',
                    'Perth Glory FC': 'Perth Glory',
                    'Auckland': 'Auckland FC',
                    'Auckland FC': 'Auckland FC',
                    'Melbourne City': 'Melbourne City',
                    'Melbourne City FC': 'Melbourne City',
                }
                
                # Special hardfix for "Wellington" if it comes as "Wellington Phoenix" already but maybe with spaces
                # Or if it comes as "Wellington" (without FC/Phoenix).
                # Note: Soccerstats sometimes uses "Wellington" and sometimes "Wellington Phoenix".
                # Our goal is to map EVERYTHING to ONE canonical name in DB.
                
                # Pre-normalization (strip spaces, etc)
                home = home.strip()
                away = away.strip()

                home = team_mapping.get(home, home)
                away = team_mapping.get(away, away)
                
                # Extra fallback for Australia names that might be slightly different in the "bydate" table
                # e.g. "Melbourne V" vs "Melbourne V." vs "Melbourne Victory"
                # This catches cases where the key in team_mapping didn't match perfectly.
                if league_obj.name == 'A League':
                     if 'Wellington' in home: home = 'Wellington Phoenix'
                     if 'Wellington' in away: away = 'Wellington Phoenix'
                     if 'Melbourne V' in home: home = 'Melbourne Victory'
                     if 'Melbourne V' in away: away = 'Melbourne Victory'
                     if 'Adelaide' in home: home = 'Adelaide United'
                     if 'Adelaide' in away: away = 'Adelaide United'
                     if 'Central Coast' in home: home = 'Central Coast Mariners'
                     if 'Central Coast' in away: away = 'Central Coast Mariners'
                     if 'Macarthur' in home: home = 'Macarthur FC'
                     if 'Macarthur' in away: away = 'Macarthur FC'
                     if 'Western United' in home: home = 'Western United'
                     if 'Western United' in away: away = 'Western United'
                     if 'WS Wanderers' in home or 'Western Sydney' in home: home = 'Western Sydney Wanderers'
                     if 'WS Wanderers' in away or 'Western Sydney' in away: away = 'Western Sydney Wanderers'
                     if 'Newcastle' in home: home = 'Newcastle Jets'
                     if 'Newcastle' in away: away = 'Newcastle Jets'
                     if 'Brisbane' in home: home = 'Brisbane Roar'
                     if 'Brisbane' in away: away = 'Brisbane Roar'
                     if 'Perth' in home: home = 'Perth Glory'
                     if 'Perth' in away: away = 'Perth Glory'
                     if 'Auckland' in home: home = 'Auckland FC'
                     if 'Auckland' in away: away = 'Auckland FC'
                     if 'Melbourne City' in home: home = 'Melbourne City'
                     if 'Melbourne City' in away: away = 'Melbourne City'
                     if 'Sydney FC' in home: home = 'Sydney FC'
                     if 'Sydney FC' in away: away = 'Sydney FC'
                
                # Hard guards: skip obvious non-team rows
                blacklist_tokens = {
                    'averages','percentages','copyright','privacy','contact','matches',
                    'defence','offence','home','away','fav','apr','feb','jan','mar',
                    'segment','points','played','goals','from','to','pts','team'
                }
                def is_garbage(name):
                    n = (name or '').strip().lower()
                    if not n: return True
                    # FIX: Don't blacklist team names that might contain 'points' or 'goals' accidentally? No, unlikely.
                    # BUT: 'Central Coast' contains 'Coast' -> OK.
                    # Check exact match for tokens or bounded?
                    # The issue: "Central Coast" might be matching something? No.
                    # "Western United" -> "Western" is not in blacklist.
                    
                    if n in blacklist_tokens: return True
                    # Only partial match if it's clearly garbage phrase
                    if 'averages' in n or 'copyright' in n: return True
                    
                    return False
                
                if is_garbage(home) or is_garbage(away):
                    continue
                
                # Heuristic to detect if it's a FINISHED match
                # A score usually looks like "2 - 1" or "2-1". 
                # A time usually looks like "16:30" or "20:00".
                # SoccerStats sometimes uses "-" for scores and ":" for times, but sometimes ":" for scores too.
                # Key difference: times usually have padding zeros (09:00), scores rarely do (9-0, not 09-00).
                # Also, scores usually have HT score nearby in parenthesis like (1-0).
                
                is_finished = False
                ht_val = ""
                for v in vals:
                    if '(' in v and ')' in v and ('-' in v or ':' in v):
                        ht_val = v
                        break
                
                # Strong signal: Half-time score present -> Finished
                if ht_val:
                    is_finished = True
                
                score_val_clean = raw_score_val.replace(' ', '').strip()
                
                # Check if it looks like a time (HH:MM)
                is_time = False
                if ':' in score_val_clean:
                    parts = score_val_clean.split(':')
                    if len(parts) == 2 and len(parts[0]) == 2 and len(parts[1]) == 2:
                        # Likely a time like 16:30
                        is_time = True
                
                if not is_time and ('-' in score_val_clean or ':' in score_val_clean):
                    # Try parsing as score
                    try:
                        sep = '-' if '-' in score_val_clean else ':'
                        p = score_val_clean.split(sep)
                        if len(p) == 2 and p[0].isdigit() and p[1].isdigit():
                            # It's a score! e.g. "2-1" or "2:1"
                            h_score = int(p[0])
                            a_score = int(p[1])
                            # Additional check: reasonable score range (0-20)
                            if 0 <= h_score <= 20 and 0 <= a_score <= 20:
                                is_finished = True
                                status = 'Finished'
                            else:
                                # Suspicious score, maybe time without leading zero? Treat as scheduled.
                                h_score = None
                                a_score = None
                                status = 'Scheduled'
                        else:
                             status = 'Scheduled'
                             h_score = None
                             a_score = None
                    except:
                        status = 'Scheduled'
                        h_score = None
                        a_score = None
                else:
                    status = 'Scheduled'
                    h_score = None
                    a_score = None

                # Force finished if we found a valid score
                if is_finished and status != 'Finished':
                     # Re-parse if needed
                     status = 'Finished'
                     # h_score/a_score should be set above
                
                # Fallback: if we have HT score but main score parsing failed
                if is_finished and (h_score is None or a_score is None):
                     # Try harder to parse raw_score_val
                     try:
                        clean = re.sub(r'[^\d\-:]', '', raw_score_val)
                        sep = '-' if '-' in clean else ':'
                        p = clean.split(sep)
                        if len(p) == 2:
                            h_score = int(p[0])
                            a_score = int(p[1])
                     except:
                        is_finished = False
                        status = 'Scheduled'

                match_date = None
                try:
                    if date_raw:
                        parts = date_raw.split()
                        if len(parts) >= 3:
                            date_str = " ".join(parts[:3])
                            # Handle date parsing more robustly
                            # Try adding year. If result is in future, subtract 1 year.
                            # BUT scraper takes 'years' arg. We should respect it.
                            # 'year' variable comes from the loop 'for year in years:'
                            
                            try:
                                # Use custom English month parsing to avoid locale issues
                                month_map = {
                                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                                }
                                parts_dt = date_str.lower().replace('.', '').split()
                                # Expected format: "Sun 1 Mar" -> parts: ["sun", "1", "mar"]
                                if len(parts_dt) >= 3:
                                    day_val = int(parts_dt[1])
                                    month_str = parts_dt[2]
                                    month = month_map.get(month_str[:3])
                                    
                                    if month:
                                        # Logic to assign correct year to the match date
                                        # European season (e.g. 2026) usually spans 2025-2026.
                                        # Matches in Aug-Dec belong to year-1 (2025).
                                        # Matches in Jan-May belong to year (2026).
                                        
                                        match_year = year
                                        if league_obj.name not in ['Brasileirão', 'A League']: # Calendar year leagues exception
                                            # Standard European season (Aug-May)
                                            # If month is >= 7 (July onwards), it belongs to the start of the season (year-1)
                                            # If month is <= 6 (June backwards), it belongs to the end of the season (year)
                                            if month >= 7:  # FIX: Julho+ = início da temporada (ano anterior). Junho = final da temporada (ano atual).
                                                match_year = year - 1
                                        else:
                                            # Calendar year leagues (e.g. 2026 season happens in 2026)
                                            # BUT A-League is actually split year (Oct-May).
                                            # If we are scraping A League 2026, it means 2025-2026 season.
                                            if league_obj.name == 'A League':
                                                if month >= 7:
                                                    match_year = year - 1
                                                else:
                                                    match_year = year
                                        
                                        naive_dt = datetime(match_year, month, day_val)
                                        match_date = timezone.make_aware(naive_dt, pytz.UTC)
                                    else:
                                        # Fallback to system locale if not in map
                                        base_dt = datetime.strptime(date_str, "%a %d %b")
                                        month = base_dt.month
                                        day = base_dt.day
                                        
                                        match_year = year
                                        if league_obj.name not in ['Brasileirão', 'A League']: 
                                            if month >= 6:
                                                match_year = year - 1
                                        else:
                                            if league_obj.name == 'A League':
                                                if month >= 7:
                                                    match_year = year - 1
                                                else:
                                                    match_year = year
                                        naive_dt = datetime(match_year, month, day)
                                        match_date = timezone.make_aware(naive_dt, pytz.UTC)
                                
                                if status == 'Scheduled' and is_time:
                                    try:
                                        parts = score_val_clean.split(':')
                                        hour = int(parts[0])
                                        minute = int(parts[1])
                                        if match_date:
                                            match_date = match_date.replace(hour=hour, minute=minute)
                                    except Exception:
                                        pass
                            except ValueError:
                                # Date format mismatch
                                pass
                except:
                    pass
                
                # Normalize team names using ODDS_API_TEAM_MAPPINGS
                home = ODDS_API_TEAM_MAPPINGS.get(home, home)
                away = ODDS_API_TEAM_MAPPINGS.get(away, away)
                
                # Use robust team retrieval function
                home_team = get_team(home, league_obj)
                away_team = get_team(away, league_obj)

                if home_team == away_team:
                    continue
                
                # DUPLICATE CHECK: Prevent processing the same match from multiple tables in the same run
                if match_date:
                    # Use date() to ignore time differences if any
                    match_key = (league_obj.id, home_team.id, away_team.id, match_date.date())
                    if match_key in self.processed_matches:
                        # self.stdout.write(f"DEBUG: Skipping duplicate match in same run: {home} vs {away} on {match_date.date()}")
                        continue
                    self.processed_matches.add(match_key)

                defaults = {
                    'home_score': h_score,
                    'away_score': a_score,
                    'status': status
                }
                if match_date:
                    defaults['date'] = match_date

                # Special handling for leagues with multiple rounds (e.g. 3rd round robin)
                # Instead of update_or_create by just (league, season, home, away), we check date proximity
                if match_date:
                    # Find potential match within +/- 5 days
                    from datetime import timedelta
                    start_range = match_date - timedelta(days=5)
                    end_range = match_date + timedelta(days=5)
                    
                    existing_match = Match.objects.filter(
                        league=league_obj,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        date__range=(start_range, end_range)
                    ).first()
                    
                    # If we found an existing match within date range, update it
                    if existing_match:
                        for k, v in defaults.items():
                            setattr(existing_match, k, v)
                        existing_match.save()
                    else:
                        # Before creating a new one, check if we have an "orphan" match
                        # (same teams, same season, but NO date set or very wrong date)
                        # This prevents duplicating if we previously scraped without date
                        orphan = Match.objects.filter(
                            league=league_obj,
                            season=season_obj,
                            home_team=home_team,
                            away_team=away_team,
                            date__isnull=True
                        ).first()
                        
                        if orphan:
                            for k, v in defaults.items():
                                setattr(orphan, k, v)
                            orphan.save()
                        else:
                            # Also check if we have a match with same teams/season but different date
                            # If the site changed the date significantly (rescheduled), we might want to update instead of create duplicate.
                            # BUT for 3rd round leagues, same teams play multiple times.
                            # So we ONLY update if the date is close (handled above) OR if we are sure it's not a new fixture.
                            # For safety in 3rd round leagues, we assume different date = new match.
                            
                            # Final check: Prevent exact duplicate creation if running multiple times quickly
                            # (Though date__range check should handle this, sometimes timezone issues affect it)
                            Match.objects.create(
                                league=league_obj,
                                season=season_obj,
                                home_team=home_team,
                                away_team=away_team,
                                **defaults
                            )
                else:
                    # Fallback to old behavior if date is missing (should be rare with new parsing)
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

    def import_from_team_page(self, url, csv_only=False):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code} for {url}")
        
        # League inference from querystring
        import urllib.parse as _up
        qs = dict(_up.parse_qsl(_up.urlsplit(url).query))
        league_slug = (qs.get('league') or '').lower()
        league_name = None
        country = None
        if league_slug == 'czechrepublic':
            league_name = 'First League'
            country = 'Republica Tcheca'
        elif league_slug == 'belgium':
            league_name = 'Pro League'
            country = 'Belgica'
        elif league_slug == 'brazil':
            league_name = 'Brasileirão'
            country = 'Brasil'
        elif league_slug == 'england':
            league_name = 'Premier League'
            country = 'Inglaterra'
        else:
            # Fallback minimal mapping
            league_name = 'First League' if 'czech' in league_slug else 'Premier League'
            country = 'Republica Tcheca' if 'czech' in league_slug else 'Inglaterra'
        
        league_obj, _ = League.objects.get_or_create(name=league_name, country=country)
        year = timezone.now().year
        
        # Parse all tables and feed to generic processor
        try:
            dfs = pd.read_html(StringIO(resp.text))
        except ValueError:
            dfs = []
        count_before = Match.objects.filter(league=league_obj).count()
        for df in dfs:
            if df.shape[1] >= 3:
                try:
                    self.process_table(df, league_obj, year)
                except Exception:
                    continue
        count_after = Match.objects.filter(league=league_obj).count()
        saved = max(0, count_after - count_before)
        if not csv_only:
            self.stdout.write(self.style.SUCCESS(f"Imported from team page. New/Updated count may include existing entries. Estimated new: {saved}"))
