import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import os
import sys
import django
from django.utils import timezone

# Setup Django environment BEFORE importing models
import os
import sys
import django

print("Starting RESULTS scraper script...", file=sys.stderr)
sys.stdout.reconfigure(line_buffering=True) # Force flush

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
    url = "https://www.soccerstats.com/results.asp?league=argentina&pmtype=bydate"
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

        # Regex for Score: "2 - 1", "0:0", etc.
        # Now supporting colon as separator
        score_pattern = re.compile(r'^\s*(\d+)\s*[:\-\s]\s*(\d+)\s*$')

        # Find "Latest results" header or similar
        # Usually SoccerStats has headers like "Latest results", "Matchday X", etc.
        # But specifically on /latest.asp, it lists recent matches.
        
        # We can scan all tables for rows that look like: Date | Home | Score | Away
        tables = soup.find_all('table')
        
        print(f"Scanning tables for results...")
        
        found_rows = 0
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 4: # Standard result row has at least 4 cols
                    continue
                
                texts = [c.get_text(strip=True) for c in cols]
                
                # Check for structure: Date | Home | Score | Away
                # Based on inspection:
                # Col 0: Date (e.g. "Fri 20 Feb")
                # Col 1: Home Team
                # Col 2: Score (e.g. "0:0") or Time
                # Col 3: Away Team
                
                date_str = texts[0]
                home_team_name = texts[1]
                score_str = texts[2]
                away_team_name = texts[3]

                # Validate Date (starts with day name)
                days_list = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                if not any(date_str.startswith(d) for d in days_list):
                    continue

                # Validate Score
                score_match = score_pattern.match(score_str)
                if not score_match:
                    continue
                
                try:
                    home_score = int(score_match.group(1))
                    away_score = int(score_match.group(2))
                    
                    # Heuristic: If scores are > 15, it's likely a time (e.g. 20:00 -> 20-0)
                    if home_score > 15 or away_score > 15:
                        # print(f"Skipping probable time: {score_str}")
                        continue
                        
                except:
                    continue
                
                # print(f"Found Candidate: {date_str} | {home_team_name} {home_score}-{away_score} {away_team_name}")
                
                # Resolve Teams
                home_team = _resolve_team(home_team_name, league)
                away_team = _resolve_team(away_team_name, league)
                
                if not home_team or not away_team:
                    # print(f"Skipping teams: {home_team_name} (Resolved: {home_team}), {away_team_name} (Resolved: {away_team})")
                    continue

                # Find the match in DB to update
                # We look for a match between these teams around this date.
                
                # Parse date to get approximate day
                try:
                    # Add year. Since the date string has no year, we assume current year.
                    # But be careful around year boundaries (Dec/Jan).
                    # "Fri 20 Feb" -> 20 Feb 2026
                    dt_str = f"{date_str} {now.year}"
                    dt_obj = datetime.strptime(dt_str, "%a %d %b %Y")
                    # Make it aware (UTC)
                    dt_obj = pytz.UTC.localize(dt_obj)

                    # Safety check: If date is in future, ignore "0-0" as it might be placeholder
                    if dt_obj.date() > timezone.now().date():
                        print(f"Skipping future match result: {home_team} {score_str} {away_team} on {dt_obj.date()}")
                        continue

                    print(f"Processing Result: {date_str} | {home_team} {home_score}-{away_score} {away_team}")
                    
                    # Define a window (e.g., +/- 3 days)
                    start_date = dt_obj - timedelta(days=3)
                    end_date = dt_obj + timedelta(days=3)
                    
                    # Try to find existing match
                    match = Match.objects.filter(
                        league=league,
                        home_team=home_team,
                        away_team=away_team,
                        date__range=(start_date, end_date)
                    ).first()
                    
                    if match:
                        if match.status != 'Finished' or match.home_score != home_score or match.away_score != away_score:
                            match.home_score = home_score
                            match.away_score = away_score
                            match.status = 'Finished'
                            match.save()
                            count_updated += 1
                            print(f"Updated Match ID {match.id}: {home_team} {home_score}-{away_score} {away_team}")
                        # else:
                        #      print(f"Match already up to date: {home_team} vs {away_team}")
                    else:
                        print(f"Match not found in DB for {home_team} vs {away_team} around {dt_obj.date()}. Creating it...")
                        # Create match if not exists
                        Match.objects.create(
                            league=league,
                            season=season,
                            home_team=home_team,
                            away_team=away_team,
                            date=dt_obj,
                            status='Finished',
                            home_score=home_score,
                            away_score=away_score
                        )
                        count_updated += 1

                except ValueError as e:
                    print(f"Date parse error for '{dt_str}': {e}")
                    continue

        print(f"Results Scrape finished. Updated/Created: {count_updated}")

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
