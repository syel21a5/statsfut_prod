"""
Passo 1: Buscar TODOS os times da API para TODAS as ligas mapeadas.
Usa a chave PRO localmente. Salva resultado em JSON para análise.
"""
import requests
import json
import time
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from matches.models import League, Team

API_KEY = '1e59f1e987bfb30f1f7538d196dcd4a0'
HEADERS = {'x-apisports-key': API_KEY}
BASE_URL = 'https://v3.football.api-sports.io'

def get_teams(league_id, season=2026):
    url = f"{BASE_URL}/teams?league={league_id}&season={season}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    data = r.json()
    if data.get('errors') or not data.get('response'):
        if season > 2024:
            time.sleep(0.3)
            return get_teams(league_id, season - 1)
        return [], season
    return [{'id': t['team']['id'], 'name': t['team']['name']} for t in data['response']], season

# Buscar TODAS as ligas com api_id
leagues = League.objects.filter(api_id__isnull=False).order_by('country', 'name')

all_data = {}
credits = 0

for league in leagues:
    print(f"\nLiga: {league.name} ({league.country}) - API ID: {league.api_id}")
    
    api_teams, season_used = get_teams(league.api_id)
    credits += 1
    time.sleep(0.3)
    
    # Buscar times do banco
    db_teams = list(Team.objects.filter(league=league).values('id', 'name', 'api_id'))
    
    all_data[f"{league.name} ({league.country})"] = {
        'league_api_id': league.api_id,
        'league_db_id': league.id,
        'season_used': season_used,
        'api_teams': api_teams,
        'db_teams': [{'id': t['id'], 'name': t['name'], 'api_id': t['api_id']} for t in db_teams],
    }
    
    print(f"  API: {len(api_teams)} times (season {season_used}) | DB: {len(db_teams)} times")

# Também buscar o Peru com o ID correto (masculino)
print("\n--- Buscando Peru Liga 1 MASCULINA ---")
# Primeiro, achar o ID correto
r = requests.get(f"{BASE_URL}/leagues?country=Peru", headers=HEADERS, timeout=15)
credits += 1
peru_leagues = r.json().get('response', [])
for pl in peru_leagues:
    print(f"  {pl['league']['id']} - {pl['league']['name']} ({pl['league']['type']})")

# Salvar JSON
with open('api_teams_dump.json', 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f"\n\nDados salvos em api_teams_dump.json")
print(f"Créditos consumidos: {credits}")
