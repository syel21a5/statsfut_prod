import os
import django
import sys
import requests
from django.utils.text import slugify

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League

def download_logos(league_name, country):
    try:
        league = League.objects.get(name=league_name, country=country)
    except League.DoesNotExist:
        print(f"Liga {league_name} não encontrada.")
        return

    country_slug = slugify(league.country)
    league_slug = slugify(league.name)
    
    # Caminho base: static/teams/franca/ligue-1/
    base_dir = os.path.join('static', 'teams', country_slug, league_slug)
    os.makedirs(base_dir, exist_ok=True)

    teams = Team.objects.filter(league=league)
    print(f"Baixando logos para {len(teams)} times de {league_name}...")

    try:
        from curl_cffi import requests as requests_cffi
    except ImportError:
        print("curl_cffi não instalado. Rodando 'pip install curl_cffi'...")
        os.system('pip install curl_cffi')
        from curl_cffi import requests as requests_cffi

    for team in teams:
        if not team.api_id:
            continue
            
        sofa_id = team.api_id.replace('sofa_', '')
        final_api_id = f"sofa_{sofa_id}"
        
        logo_url = f"https://api.sofascore.app/api/v1/team/{sofa_id}/image"
        
        file_path = os.path.join(base_dir, f"{final_api_id}.png")
        
        if os.path.exists(file_path):
            print(f"[-] Logo de {team.name} já existe, pulando.")
            continue

        try:
            # Impersonate Chrome to avoid 403
            response = requests_cffi.get(logo_url, impersonate="chrome", timeout=10)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"[+] Downloaded: {team.name} (ID: {sofa_id})")
            else:
                print(f"[!] Erro ao baixar {team.name}: Status {response.status_code}")
        except Exception as e:
            print(f"[!] Erro em {team.name}: {e}")

if __name__ == "__main__":
    download_logos("Ligue 1", "Franca")
    # download_logos("Bundesliga", "Austria")
    # download_logos("A-League Men", "Australia")
