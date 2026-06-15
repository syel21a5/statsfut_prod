import json

d = json.load(open('api_teams_dump.json', encoding='utf-8'))

for league_name, data in d.items():
    print(f"\n{'='*60}")
    print(f"LIGA: {league_name} (API ID: {data['league_api_id']}, Season: {data['season_used']})")
    print(f"{'='*60}")
    
    print("\n  --- TIMES NA API ---")
    api_names = set()
    for t in data['api_teams']:
        print(f"  {t['id']:>6} | {t['name']}")
        api_names.add(t['name'].lower())
    
    print(f"\n  --- TIMES NO BANCO (sem api_id) ---")
    unmapped = [t for t in data['db_teams'] if not t['api_id']]
    for t in unmapped:
        print(f"  DB:{t['id']:>5} | {t['name']}")
