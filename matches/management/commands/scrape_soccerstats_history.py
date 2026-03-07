
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
        parser.add_argument('--target_league', type=str, help='Process only a specific league by name (e.g. "A League")')
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
                            country=league_conf['country']
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
                # Logic for determining the correct URL based on year
                current_year = timezone.now().year
                
                # Check if this is likely the "current" season for this league
                is_current_season = False
                if league_conf['name'] in ['Brasileirão', 'A League']: # Calendar year leagues (mostly)
                     if year == current_year: is_current_season = True
                     # A-League is split year but SoccerStats might treat it differently.
                     # Assuming year param matches end year.
                else: # European leagues
                     # If we are scraping 2025 (season 24/25) and now is 2024 or 2025
                     if year == current_year or year == current_year + 1:
                         is_current_season = True
                
                # Default URL pattern
                url = f"https://www.soccerstats.com/results.asp?league={league_conf['url_base']}_{year}"
                
                # Overrides for specific leagues/conditions
                if league_conf['name'] == 'First League':
                    url = f"https://www.soccerstats.com/results.asp?league={league_conf['current_param']}&pmtype=bydate"
                
                # If scraping current season or future, try base URL without year first (often more reliable for active season)
                if is_current_season or year >= 2025:
                     # For Austria specifically, force check base url first if recent year
                     if league_conf['country'] == 'Austria' and year >= 2024:
                          url = f"https://www.soccerstats.com/results.asp?league={league_conf['url_base']}&pmtype=bydate"
                     # Generic fallback logic applied below if primary fails, but here we set primary intent

                self.stdout.write(f"Scraping {year}: {url}")

                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    
                    # If primary URL fails (404/500), try alternative
                    if response.status_code != 200:
                         self.stdout.write(self.style.ERROR(f"Failed {url}: {response.status_code}. Trying alternative URL..."))
                         
                         # Alternative 1: Base URL with bydate (Current Season usually)
                         alt_url_1 = f"https://www.soccerstats.com/results.asp?league={league_conf['url_base']}&pmtype=bydate"
                         
                         # Alternative 2: Year suffix URL (if we started with base)
                         alt_url_2 = f"https://www.soccerstats.com/results.asp?league={league_conf['url_base']}_{year}"
                         
                         if url == alt_url_1:
                             url_to_try = alt_url_2
                         else:
                             url_to_try = alt_url_1
                             
                         self.stdout.write(f"Scraping {year} (alternative): {url_to_try}")
                         response = requests.get(url_to_try, headers=headers, timeout=15)
                         
                         if response.status_code != 200:
                            self.stdout.write(self.style.ERROR(f"Alternative URL also failed: {response.status_code}"))
                            continue
                            
                    # Process response...
                    dfs_list = []
                    try:
                        dfs_list = pd.read_html(StringIO(response.text))
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f"No tables found in {url}"))
                        continue

                    count_matches = 0
                    for df_item in dfs_list:
                        if df_item.shape[1] >= 4:
                            count_matches += self.process_table(df_item, league_obj, year)
                    
                    self.stdout.write(self.style.SUCCESS(f"Saved/Updated {count_matches} matches for {year}"))

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
        count = 0
        
        # Determine columns
        # SoccerStats usually: Date | Home | Score | Away | ...
        # Or: Round | Date | Home | Score | Away | ...
        
        # Convert to string and strip
        df = df.astype(str)
        
        season_obj = Season.objects.filter(year=year).first()
        if not season_obj:
            season_obj = Season.objects.create(year=year)
        
        for idx, row in df.iterrows():
            try:
                vals = [str(x).strip() for x in row.values.tolist()]
                
                if len(vals) < 3: 
                    continue
                
                # Find score column (format "1-0" or "1:0" or "1 - 0")
                score_idx = None
                for i, v in enumerate(vals):
                    vv = v.replace('–', '-').replace('—', '-').replace('−', '-')
                    if vv and ((':' in vv) or ('-' in vv)):
                        # Remove spaces to check pattern digit-digit
                        p = vv.replace(' ', '')
                        clean_p = ''.join(c for c in p if c.isdigit() or c in ':-')
                        
                        if ':' in clean_p:
                            parts = clean_p.split(':')
                        else:
                            parts = clean_p.split('-')
                            
                        if len(parts) == 2 and all(part.isdigit() for part in parts):
                            score_idx = i
                            break
                
                if score_idx is None:
                    continue
                    
                raw_score_val = vals[score_idx]
                
                # Identify Home and Away teams
                # Usually Home is before score, Away is after
                home = None
                for i in range(score_idx - 1, -1, -1):
                    candidate = vals[i]
                    if candidate and candidate.lower() not in {'vs', 'v', 'nan', 'none', '-'}:
                        # Check if it looks like a date (e.g. "Sun 12") -> skip
                        # Simple heuristic: if it has digits, it might be date/round. Team names rarely have digits (except U23, etc)
                        # But some teams have digits (Schalke 04).
                        # Let's rely on mapping and blacklist.
                        home = candidate
                        break
                        
                away = None
                for i in range(score_idx + 1, len(vals)):
                    candidate = vals[i]
                    if candidate and candidate.lower() not in {'vs', 'v', 'nan', 'none', '-'}:
                         away = candidate
                         break
                
                if not home or not away: continue

                # Extract Date if possible (look left of Home)
                date_raw = None
                for i in range(0, score_idx):
                    candidate = vals[i]
                    # Dates usually have day name or month name
                    if any(m in candidate.lower() for m in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']):
                        date_raw = candidate
                        break
                
                # Clean Score
                h_score = None
                a_score = None
                status = 'Scheduled'
                
                clean_score = raw_score_val.replace(' ', '').replace('–', '-').replace('—', '-').replace('−', '-')
                sep = ':' if ':' in clean_score else '-'
                try:
                    parts = clean_score.split(sep)
                    h_score = int(parts[0])
                    a_score = int(parts[1])
                    status = 'Finished'
                except:
                    pass
                
                # Team Mapping
                home = ODDS_API_TEAM_MAPPINGS.get(home, home)
                away = ODDS_API_TEAM_MAPPINGS.get(away, away)
                
                # Special Australia Logic
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

                # Get/Create Teams
                # Helper function
                def get_team(name, league):
                    from django.utils.text import slugify
                    # 1. Exact
                    t = Team.objects.filter(name__iexact=name, league=league).first()
                    if t: return t
                    # 2. Slug
                    tslug = slugify(name)
                    for tm in Team.objects.filter(league=league):
                        if slugify(tm.name) == tslug: return tm
                    # 3. Contains
                    t = Team.objects.filter(league=league, name__icontains=name).first()
                    if t: return t
                    # 4. Create
                    return Team.objects.create(name=name, league=league)

                home_team = get_team(home, league_obj)
                away_team = get_team(away, league_obj)
                
                if home_team == away_team: continue
                
                # Parse Date
                match_date = None
                if date_raw:
                    try:
                         # Normalize date string
                         # e.g. "Sun 12 Mar" or "12.03"
                         dstr = date_raw.lower().replace('.', ' ').split()
                         
                         month_map = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                         }
                         
                         day = None
                         month = None
                         
                         for part in dstr:
                             if part.isdigit() and int(part) <= 31:
                                 day = int(part)
                             elif part[:3] in month_map:
                                 month = month_map[part[:3]]
                        
                         if day and month:
                             # Year logic
                             m_year = year
                             if league_obj.name not in ['Brasileirão', 'A League']:
                                 # European season logic
                                 # If match is in 2nd half of year (Jul-Dec), it's year-1 (start of season)
                                 # If match is in 1st half of year (Jan-Jun), it's year (end of season)
                                 # Wait. 'year' param is usually the END year (e.g. 2024 for 23/24).
                                 if month >= 7:
                                     m_year = year - 1
                                 else:
                                     m_year = year
                             else:
                                 # Calendar year logic
                                 if league_obj.name == 'A League':
                                     # A League starts Oct (year-1) ends May (year)
                                     if month >= 7:
                                         m_year = year - 1
                                     else:
                                         m_year = year
                                 else:
                                     # Brasileirao is full year
                                     m_year = year
                             
                             dt = datetime(m_year, month, day)
                             match_date = timezone.make_aware(dt, pytz.UTC)
                    except:
                        pass
                
                # Save Match
                defaults = {
                    'home_score': h_score,
                    'away_score': a_score,
                    'status': status
                }
                if match_date:
                    defaults['date'] = match_date
                
                # Update or Create logic
                # Try to find existing match with same teams/season
                # If date exists, check date range.
                
                match_obj = None
                if match_date:
                    start = match_date - timezone.timedelta(days=4)
                    end = match_date + timezone.timedelta(days=4)
                    match_obj = Match.objects.filter(
                        league=league_obj,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        date__range=(start, end)
                    ).first()
                
                if not match_obj:
                    # Try without date if we are creating
                    # But be careful not to duplicate if date changed drastically
                    # For safety, let's just create if not found by date-window
                    # unless it's an update of an undated match
                    match_obj = Match.objects.filter(
                        league=league_obj,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        date__isnull=True
                    ).first()
                
                if match_obj:
                    for k, v in defaults.items():
                        setattr(match_obj, k, v)
                    match_obj.save()
                else:
                    Match.objects.create(
                        league=league_obj,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        **defaults
                    )
                count += 1

            except Exception as e:
                continue
                
        return count

    def import_from_team_page(self, url, csv_only=False):
        # ... (Existing implementation) ...
        pass
