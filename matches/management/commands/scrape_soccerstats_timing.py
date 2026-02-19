

import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from matches.models import League, Team, Season, TeamGoalTiming
from django.utils import timezone

class Command(BaseCommand):
    help = 'Scrape Goals per time segment from SoccerStats.com'

    def add_arguments(self, parser):
        parser.add_argument('--league', type=str, help='League slug (e.g. argentina)', default='argentina')
        parser.add_argument('--year', type=int, help='Year (e.g. 2025)', default=2025)

    def handle(self, *args, **kwargs):
        league_slug = kwargs['league']
        year = kwargs['year']
        
        league_map = {
            'argentina': ('Liga Profesional', 'Argentina'),
            'brazil': ('Brasileirão', 'Brasil'),
            'england': ('Premier League', 'Inglaterra'),
            'belgium': ('Pro League', 'Belgica'),
            'czechrepublic': ('First League', 'Republica Tcheca'),
        }
        
        if league_slug not in league_map:
             self.stdout.write(self.style.ERROR(f"League slug '{league_slug}' not found in internal map. Using slug as name."))
             league_name = league_slug.capitalize()
             country = 'Unknown'
        else:
             league_name, country = league_map[league_slug]

        self.stdout.write(self.style.SUCCESS(f"Scraping timing for {league_name} ({year})"))

        league_obj, _ = League.objects.get_or_create(name=league_name, defaults={'country': country})
        if league_obj.country != country and country != 'Unknown':
             league_obj.country = country
             league_obj.save()

        season_obj, _ = Season.objects.get_or_create(year=year)

        current_year = timezone.now().year
        if year == current_year or year > 2024:
            url = f"https://www.soccerstats.com/timing.asp?league={league_slug}"
        else:
            url = f"https://www.soccerstats.com/timing.asp?league={league_slug}_{year}"
            
        self.stdout.write(f"URL: {url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Failed to fetch {url}: {resp.status_code}"))
                return
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find the header "Goals per time segment" and ensure it's the Overall one
            # The structure often has <h2>Goals per time segment</h2> followed by the table.
            # Home/Away tables have "(at home)" or "(away)" in the <h2>.
            
            # Strategy: Find table by content signature
            # The Overall table is the first one with 0-15, 16-30 headers
            
            target_table = None
            
            tables = soup.find_all('table')
            for i, table in enumerate(tables):
                # Use separator=' ' to ensure words didn't stick together
                text = table.get_text(separator=' ')
                # Check for key headers
                if '0-15' in text and '16-30' in text and '76-90' in text:
                     # Check if it looks like the main table (has AVG columns?)
                     # The text might be "AVG min. scored"
                     if 'AVG' in text and 'min' in text:
                         self.stdout.write(f"Found candidate table at index {i}")
                         target_table = table
                         break
            
            if not target_table:
                 self.stdout.write(self.style.ERROR("Could not find 'Goals per time segment' table via BS4"))
                 # Debug: print first few tables text to see what happened
                 for i, table in enumerate(tables[:3]):
                      self.stdout.write(f"Table {i}: {table.get_text(separator=' ')[:50]}...")
                 return

            self.process_table_bs4(target_table, league_obj, season_obj)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))

    def process_table_bs4(self, table, league_obj, season_obj):
        rows = table.find_all('tr')
        count = 0
        
        for row in rows:
            cols = row.find_all('td')
            if not cols: continue
            
            # Helper to get text
            c_texts = [c.get_text(strip=True) for c in cols]
            
            # Check if this is a team row
            # Index 0 should be team name
            team_name = c_texts[0]
            if len(team_name) < 3 or team_name in ['Overall', 'Average', 'Totals', 'Team']:
                continue
            
            # If we hit "Home" or "Away" or "Goals per time segment" inside the table, 
            # it likely means we entered a new section (Home/Away stats) and should stop.
            if team_name in ['Home', 'Away', 'Goals per time segment', 'Goals per time segment (at home)', 'Goals per time segment (away)']:
                self.stdout.write(self.style.WARNING(f"Stopping at header row: {team_name}"))
                break
            
            # Must have data columns (approx 14 columns based on snippet)
            # 0: Team, 1: GP, 2: 0-15... 7: 76-90, 8: Spacer, 9: 1H, 10: 2H, 11: Spacer, 12: AvgScored, 13: AvgConceded
            # The snippet had 14 tds (if spacers are tds)
            
            # Verify if it has "X-Y" patterns
            has_scores = any('-' in t and any(char.isdigit() for char in t) for t in c_texts[2:8])
            if not has_scores:
                continue

            try:
                # Extract Data
                # Assume standard structure
                # Handle potential spacers (empty tds)
                
                # Filter out empty spacer tds? No, index is better if fixed.
                # Snippet:
                # 0: Team
                # 1: GP
                # 2: 0-15
                # 3: 16-30
                # 4: 31-45
                # 5: 46-60
                # 6: 61-75
                # 7: 76-90
                # 8: empty
                # 9: 1st H
                # 10: 2nd H
                # 11: spacer (nbsp)
                # 12: Avg Scored
                # 13: Avg Conceded
                
                if len(cols) < 12:
                     # Maybe no spacers?
                     # Try to map by finding X-Y
                     pass

                team_obj, _ = Team.objects.get_or_create(name=team_name, league=league_obj)
                
                def parse_sc(s):
                    if not s: return (0, 0)
                    s = s.replace('–', '-').replace('—', '-')
                    if '-' not in s: return (0, 0)
                    parts = s.split('-')
                    if len(parts) != 2: return (0, 0)
                    try:
                        return (int(parts[0]), int(parts[1]))
                    except:
                        return (0, 0)

                def parse_min(s):
                    if not s: return 0
                    s = s.lower().replace('min.', '').replace('min', '').strip()
                    try:
                        return int(s)
                    except:
                        return 0

                s_0_15, c_0_15 = parse_sc(c_texts[2])
                s_16_30, c_16_30 = parse_sc(c_texts[3])
                s_31_45, c_31_45 = parse_sc(c_texts[4])
                s_46_60, c_46_60 = parse_sc(c_texts[5])
                s_61_75, c_61_75 = parse_sc(c_texts[6])
                s_76_90, c_76_90 = parse_sc(c_texts[7])
                
                # Check for spacers
                idx_1h = 8
                if c_texts[idx_1h] == '': idx_1h += 1 # Skip spacer
                
                s_1h, c_1h = parse_sc(c_texts[idx_1h])
                s_2h, c_2h = parse_sc(c_texts[idx_1h+1])
                
                idx_avg = idx_1h + 2
                if  idx_avg < len(c_texts) and (c_texts[idx_avg] == '' or 'nbsp' in str(cols[idx_avg])): idx_avg += 1
                
                # Fallback: look for "min" in the end cols
                avg_scored = 0
                avg_conceded = 0
                
                # Look for columns with "min"
                min_cols = [t for t in c_texts if 'min' in t.lower()]
                if len(min_cols) >= 2:
                    avg_scored = parse_min(min_cols[0])
                    avg_conceded = parse_min(min_cols[1])
                elif len(cols) > idx_avg + 1:
                     avg_scored = parse_min(c_texts[idx_avg])
                     avg_conceded = parse_min(c_texts[idx_avg+1])

                
                defaults = {
                        'scored_0_15': s_0_15, 'conceded_0_15': c_0_15,
                        'scored_16_30': s_16_30, 'conceded_16_30': c_16_30,
                        'scored_31_45': s_31_45, 'conceded_31_45': c_31_45,
                        'scored_46_60': s_46_60, 'conceded_46_60': c_46_60,
                        'scored_61_75': s_61_75, 'conceded_61_75': c_61_75,
                        'scored_76_90': s_76_90, 'conceded_76_90': c_76_90,
                        'scored_1st_half': s_1h, 'conceded_1st_half': c_1h,
                        'scored_2nd_half': s_2h, 'conceded_2nd_half': c_2h,
                        'avg_min_scored': avg_scored,
                        'avg_min_conceded': avg_conceded,
                }
                
                TeamGoalTiming.objects.update_or_create(
                    league=league_obj,
                    season=season_obj,
                    team=team_obj,
                    defaults=defaults
                )
                count += 1
                self.stdout.write(f"Processed {team_name}")
                
            except Exception as ex:
                self.stdout.write(self.style.WARNING(f"Skipping row {team_name}: {ex}"))
                continue
        
        self.stdout.write(self.style.SUCCESS(f"Saved {count} team timings."))

