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

print("Starting scraper script...")

# Hardcoded paths based on the error logs and environment
# The file is at: I:\GitHub\statsfut\statsfut\matches\scrapers\argentina\scrape_fixtures.py
# The project root is I:\GitHub\statsfut\statsfut (where manage.py is located)
# settings.py is at I:\GitHub\statsfut\statsfut\core\settings.py (based on search result: DJANGO_SETTINGS_MODULE='core.settings')

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
    # Fallback?
    sys.exit(1)

from django.utils import timezone
print("Imported timezone")
from matches.models import League, Season, Team, Match
print("Imported models")

def scrape_upcoming_fixtures():
    print("Entering scrape_upcoming_fixtures")
    """
    Scrapes upcoming fixtures from SoccerStats for Argentina Liga Profesional
    and saves them to the database.
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
        print("Querying database for league...")
        league = League.objects.filter(name__icontains="Liga Profesional", country__icontains="Argentina").first()
        print(f"League query result: {league}")
        if not league:
            print("League 'Liga Profesional' not found.")
            # Debug: list leagues in Argentina
            print("Leagues in Argentina:")
            for l in League.objects.filter(country="Argentina"):
                print(f"- {l.name} (ID: {l.id})")
            return

        # Get current season
        current_year = timezone.now().year
        season, _ = Season.objects.get_or_create(year=current_year)

        # SoccerStats typically puts matches in a table structure.
        # We need to find rows that look like matches.
        # Based on the screenshot, rows have date, home team, score/time, away team.
        
        # This selector is an approximation based on common SoccerStats structure.
        # We might need to adjust based on actual HTML inspection if this fails.
        # Looking for rows in the "Latest matches" section or similar tables.
        
        # Heuristic: Find tables with class 'odd' or 'even' rows or just iterate all trs
        tables = soup.find_all('table')
        
        count_created = 0
        count_updated = 0
        
        print(f"Scanning SoccerStats for {league.name} fixtures...")

        # Current year for date parsing
        now = timezone.now()

        # Regex to match time like 17:15, 19:30 (exact match)
        time_pattern = re.compile(r'^\d{1,2}:\d{2}$')

        total_rows = 0
        processed_rows = 0

        # Find the "Next matches" section
        next_matches_header = soup.find(string=re.compile("Next matches", re.IGNORECASE))
        target_table = next_matches_header.find_next('table') if next_matches_header else None
        
        # If specific table found, use it; otherwise scan all tables (carefully)
        if target_table:
            tables_to_scan = [target_table]
        else:
            print("Could not find 'Next matches' table by header. Searching for any table with future dates...")
            tables_to_scan = soup.find_all('table')

        time_pattern = re.compile(r'^\d{1,2}:\d{2}$') # Matches "22:00"

        for table in tables_to_scan:
            if not table: continue
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                
                # Extract text
                texts = [c.get_text(strip=True) for c in cols]
                
                # Debug
                # print(f"Scanning row: {texts}")

                # SoccerStats fixture row usually:
                # Date | Home | Time | Away | ...
                
                # SoccerStats fixture row variation:
                # Col 0: Date ("Thu 19 Feb")
                # Col 1: Home-Away ("Defensa y J.-Belgrano")
                # Col 2: Empty
                # Col 3: Time ("20:15")
                
                # Check for this structure
                if len(texts) >= 4 and time_pattern.match(texts[3]):
                    date_str = texts[0]
                    match_str = texts[1]
                    time_str = texts[3]
                    
                    # Split teams
                    if '-' in match_str:
                        # Handle potential hyphens in names? 
                        # Assuming simple split for now
                        parts = match_str.split('-')
                        if len(parts) == 2:
                            home_team_name = parts[0].strip()
                            away_team_name = parts[1].strip()
                        else:
                            # Heuristic: try to split in middle?
                            # Or iterate known teams?
                            # Let's just take first and last parts if multiple hyphens (rare)
                            # Or maybe it's "Team A - Team B"
                            home_team_name = parts[0].strip()
                            away_team_name = parts[-1].strip()
                            # If middle parts exist, they are lost? 
                            # E.g. "West Ham-Man Utd". 2 parts.
                            # "E. Rio Cuarto". No hyphen.
                            pass
                    else:
                        continue

                # Standard structure fallback (Date | Home | Time | Away)
                elif len(texts) >= 4 and time_pattern.match(texts[2]):
                    date_str = texts[0]
                    home_team_name = texts[1]
                    time_str = texts[2]
                    away_team_name = texts[3]
                else:
                    continue

                # Check for valid date format (e.g., "Thu 19 Feb")
                # Simple check: needs to start with day name (3 chars)
                days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                if not any(date_str.startswith(d) for d in days):
                     continue
                
                print(f"Found candidate match: {date_str} | {home_team_name} vs {away_team_name} | {time_str}")

                # Parse Date
                try:
                    # Format: "Thu 19 Feb" -> needs year
                    # We assume current year, but handle year boundary if needed (Dec/Jan)
                    
                    # SoccerStats raw time is typically UTC/Europe (e.g., 20:15).
                    # But the user sees 17:15 (Argentina/Brazil local time).
                    # So we need to subtract 3 hours from the scraped time to match the visual display.
                    
                    dt_str = f"{date_str} {now.year} {time_str}"
                    dt_obj = datetime.strptime(dt_str, "%a %d %b %Y %H:%M")
                    
                    # Treat the scraped time as if it were UTC first
                    match_date_utc = pytz.UTC.localize(dt_obj)
                    
                    # Then subtract 3 hours to get the actual match time in Argentina/Brazil
                    match_date = match_date_utc - timedelta(hours=3)

                    # If we are in December and parsing a January fixture, bump the year.
                    if now.month == 12 and dt_obj.month == 1:
                         match_date = match_date.replace(year=now.year + 1)
                    
                except ValueError as e:
                    print(f"Date parse error: {e}")
                    continue

                # Resolve Teams
                home_team = _resolve_team(home_team_name, league)
                away_team = _resolve_team(away_team_name, league)
                
                if not home_team or not away_team:
                    print(f"Skipping: {home_team_name} vs {away_team_name} (Team not found)")
                    continue

                # Create/Update Match
                # We use a custom ID or composite key
                match, created = Match.objects.update_or_create(
                    league=league,
                    season=season,
                    home_team=home_team,
                    away_team=away_team,
                    defaults={
                        'date': match_date,
                        'status': 'Scheduled', # Upcoming
                        # 'api_id': f"SS_{match_date.strftime('%Y%m%d')}_{home_team.id}_{away_team.id}" # Optional custom ID
                    }
                )
                
                if created:
                    count_created += 1
                    print(f"Created: {home_team.name} vs {away_team.name} at {match_date}")
                else:
                    count_updated += 1
                    # print(f"Updated: {home_team.name} vs {away_team.name}")

        print(f"Scrape finished. Created: {count_created}, Updated: {count_updated}")

    except Exception as e:
        print(f"Error scraping SoccerStats: {e}")

def _resolve_team(name, league):
    """
    Tries to find a team in the DB by name or alias.
    """
    # Direct match
    team = Team.objects.filter(name__iexact=name, league=league).first()
    if team:
        return team
        
    # Common mappings for SoccerStats -> DB (adjust as needed)
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
        if team:
            return team
            
    # Try partial match if not found
    team = Team.objects.filter(name__icontains=name, league=league).first()
    return team

if __name__ == "__main__":
    scrape_upcoming_fixtures()
