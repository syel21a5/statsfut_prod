import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match, Season, LeagueStanding

def import_austria_production():
    fixture_path = 'austria_fixture.json'
    if not os.path.exists(fixture_path):
        print(f"Erro: {fixture_path} não encontrado!")
        return

    print(f"Lendo {fixture_path}...")
    with open(fixture_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # IDs em Produção (Baseado no seu output do verify_prod.py)
    PROD_LEAGUE_ID = 44
    SEASON_MAP = {
        1: 24, # Fixture 2025 -> Prod ID 24
        2: 23, # Fixture 2024 -> Prod ID 23
    }

    try:
        league = League.objects.get(id=PROD_LEAGUE_ID)
    except League.DoesNotExist:
        print(f"Erro: Liga ID {PROD_LEAGUE_ID} não existe na produção!")
        return

    teams_created = 0
    matches_created = 0
    matches_updated = 0
    
    # Mapping fixture PKs to objects created/found
    fixture_team_pk_map = {} # Fixture PK -> Production Team Object

    # 1. Import Teams
    print("Sincronizando times...")
    for obj in data:
        if obj['model'] == 'matches.team':
            fields = obj['fields']
            api_id = fields.get('api_id')
            name = fields.get('name')
            
            # Upsert Team by api_id
            team, created = Team.objects.update_or_create(
                api_id=api_id,
                defaults={
                    'name': name,
                    'league': league
                }
            )
            fixture_team_pk_map[obj['pk']] = team
            if created: teams_created += 1

    print(f"Times sincronizados: {teams_created} novos criados.")

    # 2. Import Matches
    print("Sincronizando partidas...")
    for obj in data:
        if obj['model'] == 'matches.match':
            pk = obj['pk']
            fields = obj['fields']
            
            api_id = fields.get('api_id')
            fixture_home_pk = fields.get('home_team')
            fixture_away_pk = fields.get('away_team')
            fixture_season_id = fields.get('season')
            
            home_team = fixture_team_pk_map.get(fixture_home_pk)
            away_team = fixture_team_pk_map.get(fixture_away_pk)
            prod_season_id = SEASON_MAP.get(fixture_season_id)
            
            if not home_team or not away_team or not prod_season_id:
                continue

            try:
                season = Season.objects.get(id=prod_season_id)
            except Season.DoesNotExist:
                print(f"Aviso: Season ID {prod_season_id} não encontrada!")
                continue

            # Upsert Match by api_id
            match, created = Match.objects.update_or_create(
                api_id=api_id,
                defaults={
                    'league': league,
                    'season': season,
                    'home_team': home_team,
                    'away_team': away_team,
                    'date': fields.get('date'),
                    'round_name': fields.get('round_name'),
                    'status': fields.get('status'),
                    'home_score': fields.get('home_score'),
                    'away_score': fields.get('away_score'),
                    'ht_home_score': fields.get('ht_home_score'),
                    'ht_away_score': fields.get('ht_away_score'),
                    'home_shots': fields.get('home_shots'),
                    'away_shots': fields.get('away_shots'),
                    'home_shots_on_target': fields.get('home_shots_on_target'),
                    'away_shots_on_target': fields.get('away_shots_on_target'),
                    'home_corners': fields.get('home_corners'),
                    'away_corners': fields.get('away_corners'),
                    'home_fouls': fields.get('home_fouls'),
                    'away_fouls': fields.get('away_fouls'),
                    'home_yellow': fields.get('home_yellow'),
                    'away_yellow': fields.get('away_yellow'),
                    'home_red': fields.get('home_red'),
                    'away_red': fields.get('away_red'),
                }
            )
            if created: matches_created += 1
            else: matches_updated += 1

    print(f"Partidas sincronizadas: {matches_created} criadas, {matches_updated} atualizadas.")
    print("\nImportação concluída com sucesso!")

if __name__ == '__main__':
    import_austria_production()
