import os
import sys
import django  # type: ignore
import requests  # type: ignore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team  # type: ignore
from django.conf import settings  # type: ignore
from django.utils.text import slugify  # type: ignore

def fix_and_download():
    # 1. Fix Figueirense
    t = Team.objects.filter(name__icontains='Figueirense').first()
    if t:
        t.api_id = 'sofa_1970'
        t.save()
        print(f"Figueirense corrigido para {t.api_id}")
        
    # 2. Fix Duplicates for Austria (Wacker Innsbruck)
    wackers = Team.objects.filter(name__icontains='Wacker Innsbruck')
    if wackers.count() > 1:
        for w in wackers:
            if not w.api_id:
                try:
                    w.api_id = 'sofa_2118'
                    w.save()
                    print("Wacker Innsbruck sem ID corrigido!")
                except Exception:
                    pass

    # 3. Baixar imagens faltantes
    # Os que sabíamos que tavam faltando:
    # Admira Wacker Modling (2121), SC Mattersburg (2276), SV Grödig (5568)
    
    missing_teams = ['Admira Wacker Modling', 'SC Mattersburg', 'SV Grödig', 'Wacker Innsbruck']
    
    for team_name in missing_teams:
        team = Team.objects.filter(name__icontains=team_name).first()
        if not team or not team.api_id:
            continue
            
        real_id = team.api_id.replace('sofa_', '')
        url = f"https://api.sofascore.app/api/v1/team/{real_id}/image"
        
        country_slug = slugify(team.league.country)
        league_slug = slugify(team.league.name)
        folder = os.path.join(settings.BASE_DIR, 'static', 'teams', country_slug, league_slug)
        os.makedirs(folder, exist_ok=True)
        
        file_path = os.path.join(folder, f"{team.api_id}.png")
        
        if not os.path.exists(file_path):
            print(f"Baixando logo SofaScore para {team.name} ({real_id})...")
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "image/png,image/*;q=0.8"
                }
                r = requests.get(url, headers=headers)
                if r.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(r.content)
                    print(f" -> Salvo com sucesso: {file_path}")
                else:
                    print(f" -> Falha ao baixar (HTTP {r.status_code})")
            except Exception as e:
                print(f" -> Erro de rede: {str(e)}")

if __name__ == '__main__':
    fix_and_download()
