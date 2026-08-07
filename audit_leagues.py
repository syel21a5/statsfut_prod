import os, django, time
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team
from matches.api_manager import APIManager

def run_audit():
    api = APIManager()
    conf = api.apis.get('api_football_1')
    headers = api._get_headers(conf)
    base_url = conf['base_url']
    
    leagues = League.objects.filter(api_id__isnull=False).order_by('name')
    season_year = datetime.now().year
    
    print("="*70)
    print(" RELATORIO DEFINITIVO DE SINCRONIZACAO DE LIGAS (SOFASCORE x API)")
    print("="*70 + "\n")
    
    total_leagues = 0
    perfect_leagues = 0
    
    for league in leagues:
        # Pula Copas Internacionais pois a lista de times muda e eles já vêm das ligas nacionais
        if league.name in ['Copa Libertadores', 'Copa Sul-Americana', 'Champions League', 'Europa League', 'Conference League']:
            continue
            
        api_teams = []
        used_season = None
        
        # Tenta pegar a temporada atual ou anterior
        for year in [season_year, season_year - 1, season_year - 2]:
            try:
                resp = api._make_request(f"{base_url}/teams?league={league.api_id}&season={year}", headers=headers, timeout=10)
                if not resp: continue
                data = resp.json().get('response', [])
                if data:
                    api_teams = data
                    used_season = year
                    break
            except Exception:
                pass
                
        if not api_teams:
            print(f"[{league.name}] -> Nenhuma equipe encontrada na API.")
            continue
            
        total_leagues += 1
        total_api = len(api_teams)
        mapped_count = 0
        missing = []
        
        for t in api_teams:
            api_id = str(t['team']['id'])
            # Checa se o time existe no banco usando esse API_ID
            if Team.objects.filter(api_id=api_id).exists():
                mapped_count += 1
            else:
                missing.append(t['team']['name'])
                
        if mapped_count == total_api:
            print(f"🟢 {league.name} (Temp. {used_season}): {total_api} times na API -> {mapped_count} no Banco. (100% OK)")
            perfect_leagues += 1
        else:
            print(f"🔴 {league.name} (Temp. {used_season}): {total_api} times na API -> {mapped_count} no Banco.")
            print(f"    Faltou: {', '.join(missing)}")
            
        time.sleep(0.5)

    print("\n" + "="*70)
    print(f" RESUMO: {perfect_leagues} de {total_leagues} ligas nacionais estao 100% sincronizadas!")
    print("="*70)

if __name__ == '__main__':
    run_audit()
