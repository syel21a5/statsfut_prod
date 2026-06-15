import requests
import json

API_KEY = '1e59f1e987bfb30f1f7538d196dcd4a0'
HEADERS = {'x-apisports-key': API_KEY}
BASE_URL = 'https://v3.football.api-sports.io'

# Peru masculino (281)
r1 = requests.get(f"{BASE_URL}/teams?league=281&season=2026", headers=HEADERS)
peru = r1.json().get('response', [])
print("--- PERU PRIMERA DIVISION (281) ---")
for t in peru:
    print(f"  {t['team']['id']} - {t['team']['name']}")

# Argentina Primera B - times completos
r2 = requests.get(f"{BASE_URL}/teams?league=132&season=2026", headers=HEADERS)
argb = r2.json().get('response', [])
print("\n--- ARGENTINA PRIMERA B (132) ---")
for t in argb:
    print(f"  {t['team']['id']} - {t['team']['name']}")
