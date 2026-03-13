import os
import sys
import django # type: ignore
from django.utils.text import slugify # type: ignore

# Configurar Django para rodar script avulso
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team # type: ignore
from django.conf import settings # type: ignore

def audit_logos():
    countries = ['Austria', 'Australia', 'Belgica', 'Brasil', 'Suica', 'Franca']
    
    print("=== AUDITORIA GERAL DE LOGOS ===")
    
    total_teams = 0
    missing_logos = 0
    missing_ids = 0
    
    base_dir = settings.BASE_DIR
    static_dir = os.path.join(base_dir, 'static')
    
    for country in countries:
        print(f"\n[{country.upper()}]")
        teams = Team.objects.filter(league__country__icontains=country).select_related('league').order_by('name')
        
        if not teams.exists():
            print(f"  Nenhum time encontrado para a palavra-chave '{country}'.")
            continue
            
        country_missing = 0
        country_total = teams.count() # type: ignore
        
        for team in teams:
            total_teams += 1 # type: ignore
            
            if not team.api_id or not team.api_id.startswith('sofa_'):
                print(f"  [X] ID Inválido: {team.name} | API_ID Atual: '{team.api_id}'")
                missing_ids += 1 # type: ignore
                country_missing += 1 # type: ignore
                continue
                
            country_slug = slugify(team.league.country)
            league_slug = slugify(team.league.name)
            
            file_path = os.path.join(static_dir, 'teams', country_slug, league_slug, f"{team.api_id}.png")
            
            if not os.path.exists(file_path):
                print(f"  [X] Imagem Faltando: {team.name} | Esperado em: static/teams/{country_slug}/{league_slug}/{team.api_id}.png")
                missing_logos += 1 # type: ignore
                country_missing += 1 # type: ignore
                
        if country_missing == 0:
            print(f"  ✓ 100% COMPLETO: Todos os {country_total} times estão com IDs e Imagens corretas!")
        else:
            print(f"  ! ALERTA: {country_missing} de {country_total} times com problemas.")
            
    print("\n" + "="*40)
    print(f"RESUMO FINAL: {total_teams} Times Verificados")
    print(f" - Times com ID incorreto ou vazio: {missing_ids}")
    print(f" - Times com a imagem (.png) ausente no HD: {missing_logos}")
    print(f" - Times Perfeitos: {total_teams - missing_ids - missing_logos}") # type: ignore
    print("="*40)

if __name__ == '__main__':
    audit_logos()
