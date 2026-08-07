import os
import django
import sys
from datetime import datetime

# Configurar Django
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # betstats_python root
sys.path.append(parent_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, League, Team, Season
from matches.api_manager import APIManager

def verify_and_fix_league(league_name, season_year, fix=False):
    print(f"\nVerificando {league_name} - Temporada {season_year}/{season_year+1}...")
    
    # 1. Obter ID da Liga na API (Mapeamento manual por enquanto)
    # Premier League = 2021 (Football-Data), 39 (API-Football)
    # Como o api_manager agora prioriza Football-Data, devemos usar os IDs da Football-Data
    # ou o api_manager terá que ser esperto. O api_manager recebe 'league_id'.
    # Se passarmos ID 2021 para API-Football (que espera 39), vai falhar.
    # O ideal seria o manager resolver, mas vamos forçar aqui para Football-Data.
    
    LEAGUE_IDS = {
        'Premier League': 2021, # Football-Data ID
        'Serie A': 2013, # Brasileirão
        'Bundesliga': 2002,
        'La Liga': 2014,
        'Serie A (Italy)': 2019,
        'Ligue 1': 2015
    }
    
    api_league_id = LEAGUE_IDS.get(league_name)
    if not api_league_id:
        print(f"ERRO: ID da liga '{league_name}' não encontrado no mapa.")
        return

    # 2. Buscar dados OFICIAIS da API
    manager = APIManager()
    try:
        print("Buscando dados oficiais da API-Football...")
        # season year na API é o ano de inicio (ex: 2024 para 24/25)
        # Se o user diz "2025/2026", o ano é 2025.
        official_fixtures = manager.get_league_season_fixtures(api_league_id, season_year)
        print(f"Recuperados {len(official_fixtures)} jogos da API.")
        if not official_fixtures:
             print(f"DEBUG: Tentando buscar com 'season={season_year-1}' caso a user tenha se enganado...")
             official_fixtures = manager.get_league_season_fixtures(api_league_id, season_year-1)
             print(f"Recuperados {len(official_fixtures)} jogos da API (Season {season_year-1}).")
    except Exception as e:
        print(f"Erro ao buscar na API: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Buscar dados LOCAIS do Banco de Dados
    try:
        league_obj = League.objects.get(name__icontains=league_name) # match 'Premier League' from 'Inglaterra - Premier League' etc
        season_obj = Season.objects.get(year=season_year + 1) # DB usa ano de finalização (25/26 -> 2026)
    except League.DoesNotExist:
        print(f"Liga '{league_name}' não encontrada no banco local.")
        return
    except Season.DoesNotExist:
        print(f"Temporada final {season_year + 1} não encontrada no banco local.")
        return

    local_matches = Match.objects.filter(league=league_obj, season=season_obj)
    print(f"Encontrados {local_matches.count()} jogos no banco local.")

    # 4. Comparar
    discrepancies = 0
    fixed_count = 0
    
    # Criar dict para busca rápida na API por data + times (fuzzy) ou ID se tiver
    matched_count = 0
    
    # Debug Arsenal specific
    arsenal_losses_api = 0
    arsenal_losses_local = 0
    
    # Iterar sobre locais
    for match in local_matches:
        if not match.date:
            continue
            
        m_date = match.date.strftime('%Y-%m-%d')
        # Tentar casar pelo nome exato (pode falhar se nomes forem diferentes)
        
        api_match = None
        
        if match.api_id:
            api_match = next((f for f in official_fixtures if str(f['id']) == str(match.api_id)), None)
        
        if not api_match:
            candidates = [f for f in official_fixtures if f['date'][:10] == m_date]
            for cand in candidates:
                # Normalizar nomes para comparação: "Arsenal FC" -> "Arsenal"
                # Check se um está contido no outro
                
                # Suporte a Football-Data (chaves homeTeam/awayTeam) e API-Football (teams.home.name)
                # O manager normaliza para: 'home_team', 'away_team', 'date' ...
                # Verifique se o manager normalizou football-data corretamente.
                # O metodo _normalize_football_data usa: 'home_team': match['homeTeam']['name']
                
                api_home = cand.get('home_team')
                if not api_home: # Raw dict if normalization failed or skipped?
                     # Se viemos do api_football_data raw no verify_matches (não deveria, pois api_manager normaliza)
                     # Mas vamos checar
                     pass
                
                if match.home_team.name in api_home or api_home in match.home_team.name:
                     api_match = cand
                     break
        
        if api_match:
            matched_count += 1
            # Comparar Scores
            api_home = api_match['home_score']
            api_away = api_match['away_score']
            
            # Pula jogos não terminados na API
            if api_match['status'] not in ['FT', 'AET', 'PEN', 'FINISHED']:
                continue

            # Checar Arsenal losses (somente finalizados)
            if "Arsenal" in match.home_team.name or "Arsenal" in match.away_team.name:
                 # Local loss?
                 if match.home_score is not None and match.away_score is not None:
                     if "Arsenal" in match.home_team.name and match.home_score < match.away_score: reduced_res = 'L'
                     elif "Arsenal" in match.away_team.name and match.away_score < match.home_score: reduced_res = 'L'
                     else: reduced_res = 'ND'
                     if reduced_res == 'L': arsenal_losses_local += 1
                 
                 # API loss?
                 if "Arsenal" in api_match['home_team'] and api_home < api_away:
                      arsenal_losses_api += 1
                 elif "Arsenal" in api_match['away_team'] and api_away < api_home:
                      arsenal_losses_api += 1

            has_error = False
            msg = []
            
            if match.home_score != api_home:
                has_error = True
                msg.append(f"Home: {match.home_score} -> {api_home}")
            
            if match.away_score != api_away:
                has_error = True
                msg.append(f"Away: {match.away_score} -> {api_away}")
                
            if has_error:
                discrepancies += 1
                print(f"[DISCREPÂNCIA] {m_date} | {match.home_team} x {match.away_team}")
                print(f"  Local: {match.home_score}-{match.away_score} | API: {api_home}-{api_away} ({api_match['status']})")
                
                if fix:
                    match.home_score = api_home
                    match.away_score = api_away
                    match.status = "Finished"
                    match.api_id = api_match['id'] 
                    match.save()
                    print("  -> CORRIGIDO.")
                    fixed_count += 1
        else:
            # print(f"Aviso: Não encontrei correspondência na API para {match}")
            pass

    print(f"\nResumo: {discrepancies} discrepâncias encontradas.")
    print(f"Jogos pareados (Local <-> API): {matched_count} de {local_matches.count()}")
    print(f"Arsenal Losses (Verificado nos matched): Local={arsenal_losses_local} vs API={arsenal_losses_api}")
    if fix:
        print(f"Foram corrigidos {fixed_count} jogos.")

if __name__ == "__main__":
    # Exemplo: Premier League 2024 (Season 24/25) 
    # O usuário falou 2025/2026? Se for futuro, nao tem resultado.
    # Mas ele falou "na temporada atual que é 2025/2026 mostra o arsenal com uma derrota".
    # Estamos em Jan 2026. Então a temporada é a "2025" da API (que começa mid-2025 e acaba mid-2026).
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--league', type=str, default="Premier League")
    parser.add_argument('--year', type=int, default=2025)
    parser.add_argument('--fix', action='store_true')
    
    args = parser.parse_args()
    
    verify_and_fix_league(args.league, args.year, args.fix)
