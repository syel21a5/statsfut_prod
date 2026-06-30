import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team
from django.conf import settings
from django.utils.text import slugify

def download_logo(sofascore_id, country_name, file_name):
    # Usando o subdomínio correto img.sofascore.com
    url = f"https://img.sofascore.com/api/v1/team/{sofascore_id}/image"
    country_slug = slugify(country_name)
    
    # Pasta final: static/teams/{country_slug}/ (a mesma mapeada pelo model)
    folder = os.path.join(settings.BASE_DIR, 'static', 'teams', country_slug)
    os.makedirs(folder, exist_ok=True)
    
    file_path = os.path.join(folder, f"{file_name}.png")
    
    print(f"Baixando logo SofaScore para {file_name} ({sofascore_id})...")
    try:
        from curl_cffi import requests as requests_cffi
        # Impersonate Chrome para burlar o Cloudflare (403)
        r = requests_cffi.get(url, impersonate="chrome", timeout=15)
        if r.status_code == 200 and len(r.content) > 100:
            with open(file_path, 'wb') as f:
                f.write(r.content)
            print(f" -> Salvo com sucesso em: {file_path}")
            return True
        else:
            print(f" -> Falha ao baixar (HTTP {r.status_code})")
    except Exception as e:
        print(f" -> Erro ao baixar logo: {str(e)}")
    return False

def main():
    # 1. Athletic Club (Série B)
    athletic = Team.objects.filter(name__iexact='Athletic Club', league__name__icontains='Série B').first()
    if athletic:
        athletic.api_id = 'sofa_342775'  # Athletic Club MG ID
        athletic.save()
        print("Athletic Club Série B ID atualizado para sofa_342775.")
        download_logo('342775', 'Brazil', 'sofa_342775')
    else:
        print("Athletic Club Série B não encontrado.")

    # 2. CSD Flandria (Argentina - Primera B)
    flandria = Team.objects.filter(name__iexact='CSD Flandria').first()
    if flandria:
        flandria.api_id = 'sofa_112505'  # CSD Flandria real ID
        flandria.save()
        print("CSD Flandria ID atualizado para sofa_112505.")
        download_logo('112505', 'Argentina', 'sofa_112505')
    else:
        print("CSD Flandria não encontrado.")
        
    # 3. Santos (Brasileirão)
    santos = Team.objects.filter(name__iexact='Santos', league__name__icontains='Série B').first()
    if not santos:
        santos = Team.objects.filter(name__iexact='Santos').first()
        
    if santos:
        santos.api_id = 'sofa_1968'  # Santos FC ID
        santos.save()
        print("Santos ID atualizado para sofa_1968.")
        download_logo('1968', 'Brazil', 'sofa_1968')
    else:
        print("Santos não encontrado.")

if __name__ == '__main__':
    main()
