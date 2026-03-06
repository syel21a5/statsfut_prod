import os
import django
import time
from urllib.parse import urlparse
from curl_cffi import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import Team, League
from django.utils.text import slugify

def download_logos():
    session = requests.Session(impersonate="chrome110")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    })

    # Get all teams that have a SofaScore ID
    teams = Team.objects.filter(api_id__startswith='sofa_')
    
    # Base directory for static logos
    base_dir = os.path.join(os.path.dirname(__file__), 'matches', 'static', 'teams')
    
    downloaded = 0
    skipped = 0
    errors = 0

    print(f"Encontrados {teams.count()} times para processar.")

    for team in teams:
        # Extract ID (e.g., 'sofa_2934' -> '2934')
        sofa_id = team.api_id.replace('sofa_', '')
        
        country_slug = slugify(team.league.country)
        league_slug = slugify(team.league.name)
        
        # Target Path: matches/static/teams/australia/a-league-men/sofa_2934.png
        dir_path = os.path.join(base_dir, country_slug, league_slug)
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, f"{team.api_id}.png")
        
        if os.path.exists(file_path):
            # print(f"Pulando {team.name} ({team.api_id}) - Já existe.")
            skipped += 1
            continue
            
        url = f"https://api.sofascore.app/api/v1/team/{sofa_id}/image"
        
        try:
            time.sleep(1) # Be gentle with the API
            response = session.get(url, timeout=15)
            
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"[{downloaded+1}] Baixado: {team.name} ({country_slug}/{league_slug})")
                downloaded += 1
            else:
                print(f"[ERRO] {team.name}: HTTP {response.status_code}")
                errors += 1
        except Exception as e:
            print(f"[ERRO] {team.name}: Falha na conexão - {e}")
            errors += 1

    print("\nResumo do Download:")
    print(f"Baixados: {downloaded}")
    print(f"Pulados (já existiam): {skipped}")
    print(f"Erros: {errors}")

if __name__ == '__main__':
    download_logos()
