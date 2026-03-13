import os
import sys
import django
from django.utils.text import slugify

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team
from django.conf import settings

def find_orphans():
    static_dir = os.path.join(settings.BASE_DIR, 'static')
    countries = ['Austria', 'Australia', 'Belgica', 'Brasil', 'Suica', 'Franca']
    
    print("=== ARQUIVOS .PNG ÓRFÃOS (Sem Time no Banco) ===")
    for country in countries:
        teams = Team.objects.filter(league__country__icontains=country)
        if not teams.exists(): 
            continue
        
        country_slug = slugify(teams[0].league.country)
        league_slug = slugify(teams[0].league.name)
        folder = os.path.join(static_dir, 'teams', country_slug, league_slug)
        
        if not os.path.exists(folder): 
            print(f"[{country.upper()}] Pasta não encontrada: {folder}")
            continue
        
        assigned_ids = set(t.api_id for t in teams if t.api_id)
        
        files = [f for f in os.listdir(folder) if f.endswith('.png')]
        orphans = [f for f in files if f.replace('.png', '') not in assigned_ids]
        
        print(f"\n[{country.upper()}] - {len(orphans)} imagens sem dono:")
        for f in orphans:
            print(f"  {f}")

if __name__ == '__main__':
    find_orphans()
