import os
import sys
import django
from django.db import IntegrityError

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
    
    print(f"Baixando logo SofaScore para {file_name} ({sofascore_id}) no país {country_name}...")
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

def fix_team_logo(team, sofascore_id):
    if not team:
        return False
        
    api_id_str = f"sofa_{sofascore_id}"
    
    # Atualiza o ID da API, ignorando caso outro time já o possua
    try:
        if team.api_id != api_id_str:
            team.api_id = api_id_str
            team.save()
            print(f"{team.name} ID atualizado para {api_id_str}.")
    except IntegrityError:
        print(f"Aviso: O ID {api_id_str} já está sendo usado por outro time no banco de dados. Pulando a atualização do api_id para {team.name}.")
    
    # Obtém o nome do país de forma dinâmica, para evitar erros de digitação como 'Brazil' vs 'Brasil'
    country_name = 'Brasil' # Padrão
    if team.league and hasattr(team.league, 'country') and team.league.country:
        if hasattr(team.league.country, 'name'):
            country_name = team.league.country.name
        else:
            country_name = str(team.league.country)
            
    download_logo(sofascore_id, country_name, api_id_str)
    return True

def main():
    # 1. Athletic Club (Série B)
    athletic = Team.objects.filter(name__iexact='Athletic Club', league__name__icontains='Série B').first()
    if not fix_team_logo(athletic, '342775'):
        print("Athletic Club Série B não encontrado.")

    # 2. CSD Flandria (Argentina - Primera B)
    flandria = Team.objects.filter(name__iexact='CSD Flandria').first()
    if not fix_team_logo(flandria, '112505'):
        print("CSD Flandria não encontrado.")
        
    # 3. Santos (Série B ou geral)
    santos = Team.objects.filter(name__iexact='Santos', league__name__icontains='Série B').first()
    if not santos:
        santos = Team.objects.filter(name__iexact='Santos').first()
        
    if not fix_team_logo(santos, '1968'):
        print("Santos não encontrado.")

if __name__ == '__main__':
    main()
