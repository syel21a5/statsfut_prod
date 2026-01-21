import os
import requests
import sys

# Load env vars manually or via django? Django is easier
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

key = os.getenv('FOOTBALL_DATA_KEY')
print(f"Key present: {bool(key)}")

if key:
    headers = {'X-Auth-Token': key}
    # PL = 2021
    # season 2025 usually means 25/26. Or maybe current season.
    # football-data.org current season logic:
    # try 2025 first.
    url = "https://api.football-data.org/v4/competitions/2021/matches?season=2025"
    print(f"Requesting {url}...")
    resp = requests.get(url, headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        matches = data.get('matches', [])
        print(f"Matches found: {len(matches)}")
        if len(matches) == 0:
             print("Trying season 2024...")
             url2 = "https://api.football-data.org/v4/competitions/2021/matches?season=2024"
             resp2 = requests.get(url2, headers=headers)
             print(f"Status 2024: {resp2.status_code}")
             if resp2.status_code == 200:
                 print(f"Matches found 2024: {resp2.json().get('count')}")
    else:
        print(f"Error: {resp.text}")
