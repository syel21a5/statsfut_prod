import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import os
import sys
import django

# Setup Django environment BEFORE importing models
import os
import sys
import django

print("Starting RESULTS scraper script...")

# Let's look at where we are.
current_dir = os.path.dirname(os.path.abspath(__file__))
# .../argentina
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
# .../statsfut (the one containing matches app and manage.py)

# Add base_dir to path so we can import 'core' and 'matches'
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# Set settings module to 'core.settings' (standard for this project)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    django.setup()
    print("Django setup successful")
except Exception as e:
    print(f"Django setup failed: {e}")
    sys.exit(1)

from django.utils import timezone
from matches.models import League, Season, Team, Match

def scrape_latest_results():
    print("Entering scrape_latest_results")
    """
    Scrapes LATEST RESULTS from SoccerStats for Argentina Liga Profesional
    and updates matches in the database (setting status=Finished and scores).
    """
    url = "https://www.soccerstats.com/latest.asp?league=argentina"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Response status: {response.status_code}")
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        print("Parsed HTML")

        # Find the league object
        league = League.objects.filter(name__icontains="Liga Profesional", country__icontains="Argentina").first()
        if not league:
            print("League 'Liga Profesional' not found.")
            return

        # Get current season
        current_year = timezone.now().year
        season, _ = Season.objects.get_or_create(year=current_year)
        
        count_updated = 0
        now = timezone.now()

        # Regex for Score: "2 - 1", "0-0", etc.
        score_pattern = re.compile(r'^\s*(\d+)\s*-\s*(\d+)\s*$')

        # Find "Latest results" header or similar
        # Usually SoccerStats has headers like "Latest results", "Matchday X", etc.
        # But specifically on /latest.asp, it lists recent matches.
        
        # We can scan all tables for rows that look like: Date | Home | Score | Away
        tables = soup.find_all('table')
        
        print(f"Scanning tables for results...")

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                
                texts = [c.get_text(strip=True) for c in cols]
                
                # Check for structure: Date | Home | Score | Away
                # Variation 1: Date | Home | Score | Away
                # Variation 2: Date | Home-Away | Score (unlikely for results)
                
                date_str = None
                home_team_name = None
                away_team_name = None
                home_score = None
                away_score = None
                
                # Try to find score in column 2 or 3
                score_match = None
                score_col_idx = -1
                
                if len(texts) >= 4:
                    # Check col 2 (0-based) for score
                    if score_pattern.match(texts[2]):
                        score_match = score_pattern.match(texts[2])
                        score_col_idx = 2
                        date_str = texts[0]
                        home_team_name = texts[1]
                        away_team_name = texts[3]
                    # Check col 3 for score (maybe there is a spacer?)
                    elif score_pattern.match(texts[3]):
                        score_match = score_pattern.match(texts[3])
                        score_col_idx = 3
                        date_str = texts[0]
                        # Assume col 1 is Home - Away? No, usually separate cols if score is separate.
                        # Maybe: Date | Home | Time/Score | Away
                        # If score is in col 3, maybe col 1 is Home, col 2 is empty?
                        if len(texts[2]) == 0: # Empty col 2
                            home_team_name = texts[1]
                            away_team_name = texts[4] if len(texts) > 4 else None # Guessing
                        else:
                            # Maybe: Date | Home | ... | Score | Away
                            pass
                
                if not score_match or not home_team_name or not away_team_name:
                    continue
                
                # Parse Score
                try:
                    home_score = int(score_match.group(1))
                    away_score = int(score_match.group(2))
                except:
                    continue
                    
                # Validate Date (starts with day name)
                days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                if not any(date_str.startswith(d) for d in days):
                    continue

                print(f"Found Result: {date_str} | {home_team_name} {home_score}-{away_score} {away_team_name}")
                
                # Resolve Teams
                home_team = _resolve_team(home_team_name, league)
                away_team = _resolve_team(away_team_name, league)
                
                if not home_team or not away_team:
                    print(f"Skipping teams: {home_team_name}, {away_team_name}")
                    continue

                # Find the match in DB to update
                # We look for a match between these teams around this date.
                # Since date formats might slightly differ or timezone issues, we look for matches
                # within a few days window, or just by teams and status='Scheduled' or 'Finished'.
                
                # First, parse date to get approximate day
                try:
                    dt_str = f"{date_str} {now.year}"
                    # Assuming time is not in date_str for results
                    dt_obj = datetime.strptime(dt_str, "%a %d %b %Y")
                    # Make it aware
                    dt_obj = pytz.UTC.localize(dt_obj)
                    
                    # Define a window (e.g., +/- 2 days)
                    start_date = dt_obj - timedelta(days=2)
                    end_date = dt_obj + timedelta(days=2)
                    
                    # Find match
                    match = Match.objects.filter(
                        league=league,
                        home_team=home_team,
                        away_team=away_team,
                        date__range=(start_date, end_date)
                    ).first()
                    
                    if match:
                        # Update Match
                        match.home_team_score = home_score
                        match.away_team_score = away_score
                        match.status = 'Finished'
                        match.save()
                        count_updated += 1
                        print(f"Updated Match ID {match.id}: {home_team} {home_score}-{away_score} {away_team}")
                    else:
                        print(f"Match not found in DB for {home_team} vs {away_team} around {dt_obj.date()}")
                        # Optionally create it? 
                        # Usually better to only update existing ones to avoid duplicates if dates are wildly off.
                        # But if it's missing, maybe we should create it as Finished.
                        pass

                except ValueError as e:
                    print(f"Date parse error: {e}")
                    continue

        print(f"Results Scrape finished. Updated: {count_updated}")

    except Exception as e:
        print(f"Error scraping SoccerStats Results: {e}")

def _resolve_team(name, league):
    # Same mapping logic as scrape_fixtures.py
    # Copying the mapping dict for consistency
    mappings = {
        "Defensa y J.": "Defensa y Justicia",
        "Union Santa Fe": "Union de Santa Fe",
        "San Lorenzo": "San Lorenzo",
        "Racing Club": "Racing Club",
        "Huracan": "Huracan",
        "Sarmiento": "Sarmiento Junin",
        "T. de Cordoba": "Talleres Cordoba",
        "G. Mendoza": "Gimnasia Mendoza",
        "A. Tucuman": "Atl. Tucuman",
        "E. Rio Cuarto": "Estudiantes Rio Cuarto",
        "I. Rivadavia": "Ind. Rivadavia",
        "Belgrano": "Belgrano",
        "Gimnasia": "Gimnasia L.P.",
        "Estudiantes": "Estudiantes L.P.",
        "Boca Juniors": "Boca Juniors",
        "Platense": "Platense",
        "Instituto": "Instituto",
        "Central Cordoba": "Central Cordoba",
        "Rosario Central": "Rosario Central",
        "Barracas C.": "Barracas Central",
        "D. Riestra": "Dep. Riestra",
        "Newells": "Newells Old Boys",
        "Independiente": "Independiente",
        "Argentinos J.": "Argentinos Jrs",
        "Velez Sarsfield": "Velez Sarsfield",
        "Lanus": "Lanus",
        "Banfield": "Banfield",
        "Tigre": "Tigre",
        "River Plate": "River Plate",
    }
    
    mapped_name = mappings.get(name)
    if mapped_name:
        team = Team.objects.filter(name__iexact=mapped_name, league=league).first()
        if team: return team
            
    team = Team.objects.filter(name__iexact=name, league=league).first()
    if team: return team
    
    team = Team.objects.filter(name__icontains=name, league=league).first()
    return team

if __name__ == "__main__":
    scrape_latest_results()
