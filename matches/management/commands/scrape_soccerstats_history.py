
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
from matches.models import League, Team, Match, Season
from django.utils import timezone

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
            },
            {
                'name': 'Bundesliga',
                'country': 'Austria',
                'url_base': 'austria',
                'current_param': 'austria'
            },
            {
                'name': 'Super League',
                'country': 'Suica',
                'url_base': 'switzerland',
                'current_param': 'switzerland'
            },
            {
                'name': 'Superliga',
                'country': 'Dinamarca',
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
                    league_obj, _ = League.objects.get_or_create(
                        name=league_conf['name'], 
                        country=league_conf['country']
                    )
                    self.stdout.write(f"DEBUG: League object retrieved: {league_obj}")
                    sys.stdout.flush()
                except Exception as e:
                    self.stdout.write(f"ERROR: DB Error: {e}")
                    sys.stdout.flush()
                    continue

            for year in years:
                if league_conf['name'] == 'First League':
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['current_param']}"
                elif (league_conf['name'] == 'Brasileirão' and year == 2026) or \
                     (league_conf['name'] == 'Pro League' and year == 2026) or \
                     (league_conf['name'] == 'Super League' and year == 2026) or \
                     (league_conf['name'] == 'Superliga' and year == 2026):
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['current_param']}"
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
                    elif (league_conf['name'] == 'First League' or league_conf['name'] == 'Super League' or league_conf['name'] == 'Superliga') and year == 2026:
                        for m in range(1, 13):
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
                    'Red Bull Salzburg': 'RB Salzburg',
                    'Salzburg': 'RB Salzburg',
                    'Sturm Graz': 'Sturm Graz',
                    'SK Sturm Graz': 'Sturm Graz',
                    'LASK': 'LASK',
                    'LASK Linz': 'LASK',
                    'Rapid Wien': 'Rapid Vienna',
                    'Rapid Vienna': 'Rapid Vienna',
                    'Austria Wien': 'Austria Vienna',
                    'Austria Vienna': 'Austria Vienna',
                    'Wolfsberger AC': 'Wolfsberger AC',
                    'WAC': 'Wolfsberger AC',
                    'SK Austria Klagenfurt': 'Austria Klagenfurt',
                    'A. Klagenfurt': 'Austria Klagenfurt',
                    'TSV Hartberg': 'Hartberg',
                    'Hartberg': 'Hartberg',
                    'SCR Altach': 'Altach',
                    'Altach': 'Altach',
                    'FC Blau Weiss Linz': 'Blau-Weiss Linz',
                    'BW Linz': 'Blau-Weiss Linz',
                    'WSG Tirol': 'WSG Tirol',
                    'Grazer AK': 'Grazer AK',
                    'GAK': 'Grazer AK',
                    'Austria Lustenau': 'Austria Lustenau',
                    'A. Lustenau': 'Austria Lustenau',

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
                ht_val = ""
                for v in vals:
                    if '(' in v and ')' in v:
                        ht_val = v
                        break
                if '(' in ht_val and ')' in ht_val:
                    is_finished = True
                elif ('-' in score_val or ':' in score_val) and not (len(score_val) == 5 and score_val[2] == ':'):
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
                    if date_raw:
                        parts = date_raw.split()
                        if len(parts) >= 3:
                            date_str = " ".join(parts[:3])
                            base_dt = datetime.strptime(date_str, "%a %d %b")
                            month = base_dt.month
                            day = base_dt.day
                            if league_obj.name == 'Brasileirão':
                                year_val = year
                            else:
                                # European seasons often start in July
                                year_val = year - 1 if month >= 7 else year
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
