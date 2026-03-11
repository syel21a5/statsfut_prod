import os
import django
import sys
from pprint import pprint

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League, Match

def diagnose_db():
    print("=== LIGAS ===")
    for l in League.objects.all():
        print(f"ID: {l.id} | Name: '{l.name}' | Country: '{l.country}'")
        
    print("\n=== LIGUE 1 TEAMS ===")
    fr_leagues = League.objects.filter(country__icontains='franc')
    if not fr_leagues:
        fr_leagues = League.objects.filter(name__icontains='ligue')
        
    for l in fr_leagues:
        print(f"\nLiga encontrada: {l.name} ({l.country})")
        teams = Team.objects.filter(league=l).order_by('name')
        for t in teams:
            print(f"  - [{t.id}] '{t.name}' (api_id: {t.api_id}) | Jogos: {Match.objects.filter(home_team=t).count() + Match.objects.filter(away_team=t).count()}")

    print("\n=== AUSTRIA TEAMS ===")
    at_leagues = League.objects.filter(country__icontains='austr')
    for l in at_leagues:
        print(f"\nLiga encontrada: {l.name} ({l.country})")
        teams = Team.objects.filter(league=l).order_by('name')
        for t in teams:
             print(f"  - [{t.id}] '{t.name}' (api_id: {t.api_id}) | Jogos: {Match.objects.filter(home_team=t).count() + Match.objects.filter(away_team=t).count()}")

if __name__ == "__main__":
    diagnose_db()
