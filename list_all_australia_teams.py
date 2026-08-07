from matches.models import Team, League

try:
    league = League.objects.get(name="A League", country="Australia")
    teams = Team.objects.filter(league=league)
    
    print(f"--- TIMES NA A-LEAGUE ({teams.count()}) ---")
    for t in teams:
        print(f"ID: {t.id} | Nome: '{t.name}' | API_ID: {t.api_id}")

except Exception as e:
    print(f"ERRO: {e}")
