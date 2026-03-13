import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League

# Countries to check
target_countries = ['Suica', 'Belgica', 'Brasil']

print("=== DIAGNÓSTICO DE TIMES DA PRODUÇÃO ===")
print("Por favor, copie e cole este resultado para o assistente AI.\n")

for country in target_countries:
    print(f"--- LIGAS EM: {country.upper()} ---")
    leagues = League.objects.filter(country__icontains=country)
    
    if not leagues.exists():
        print(f"  [AVISO] Nenhuma liga encontrada para o país: {country}")
        continue
        
    for league in leagues:
        print(f"Liga: {league.name} (ID: {league.id})")
        teams = Team.objects.filter(league=league).order_by('name')
        
        print(f"  Total de times: {teams.count()}")
        for t in teams:
            api_str = t.api_id if t.api_id else "NENHUM"
            print(f"    - ID DB: {t.id:4d} | Nome: {t.name:<25} | API_ID: {api_str}")
    print("\n")
