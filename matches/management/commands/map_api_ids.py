from django.core.management.base import BaseCommand
from matches.models import League, Team
from matches.api_manager import APIManager
import difflib

class Command(BaseCommand):
    help = 'Mapeia ligas e times do banco com IDs da API-Football'

    def add_arguments(self, parser):
        parser.add_argument('--country', type=str, help='País para mapear (Ex: Brazil, England)')
        parser.add_argument('--league_id', type=int, help='ID de uma liga específica no banco para mapear times')

    def handle(self, *args, **options):
        api = APIManager()
        if not api.USE_API_FOOTBALL:
            self.stdout.write(self.style.ERROR("API-Football está desativada no APIManager."))
            return

        country = options.get('country')
        league_id_db = options.get('league_id')

        if not country and not league_id_db:
            self.stdout.write(self.style.ERROR("Forneça --country ou --league_id"))
            return

        api_config = api.apis.get('api_football_1')
        if not api_config or not api_config.get('key'):
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY não encontrada."))
            return

        headers = api._get_headers(api_config)

        if country:
            self._map_leagues_for_country(api, api_config, headers, country)
        
        if league_id_db:
            self._map_teams_for_league(api, api_config, headers, league_id_db)

    def _map_leagues_for_country(self, api, api_config, headers, country):
        self.stdout.write(self.style.SUCCESS(f"\nBuscando ligas ativas na API para: {country}"))
        
        # 1. Buscar ligas do país na API
        params = {'country': country, 'type': 'League'}
        try:
            resp = api._make_request(f"{api_config['base_url']}/leagues", headers=headers, params=params, timeout=15)
            api._increment_usage('api_football_1')
            if resp.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Erro ao buscar ligas: {resp.status_code}"))
                return
            
            data_json = resp.json()
            if 'errors' in data_json and data_json['errors']:
                self.stdout.write(self.style.ERROR(f"Erro da API: {data_json['errors']}"))
                return
                
            data = data_json.get('response', [])
            api_leagues = []
            for item in data:
                # Filtrar se tem temporada atual
                if any(s.get('current') for s in item.get('seasons', [])):
                    api_leagues.append({
                        'id': str(item['league']['id']),
                        'name': item['league']['name']
                    })
            
            if not api_leagues:
                self.stdout.write(self.style.WARNING("Nenhuma liga ativa encontrada na API."))
                return
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Exceção: {e}"))
            return

        # 2. Buscar ligas no nosso Banco que não têm api_id
        db_leagues = League.objects.filter(api_id__isnull=True)
        if not db_leagues.exists():
            self.stdout.write(self.style.SUCCESS(f"Todas as ligas no banco já possuem api_id!"))
            return

        self.stdout.write(f"Encontradas {db_leagues.count()} ligas no banco sem api_id. Iniciando fuzzy matching...\n")

        for db_l in db_leagues:
            best_match = None
            best_score = 0
            
            for al in api_leagues:
                # Calcular similaridade (difflib)
                score = difflib.SequenceMatcher(None, db_l.name.lower(), al['name'].lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = al

            if best_match and best_score > 0.65:
                db_l.api_id = best_match['id']
                db_l.save()
                self.stdout.write(self.style.SUCCESS(f"✅ Mapeado: Banco '{db_l.name}' -> API '{best_match['name']}' (ID: {best_match['id']}, Score: {best_score:.2f})"))
            else:
                self.stdout.write(self.style.WARNING(f"❌ Não mapeado com certeza: Banco '{db_l.name}'. Melhor match: '{best_match['name'] if best_match else 'Nenhum'}' (Score: {best_score:.2f})"))

    def _map_teams_for_league(self, api, api_config, headers, league_id_db):
        try:
            db_league = League.objects.get(id=league_id_db)
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR("Liga não encontrada no banco."))
            return

        if not db_league.api_id:
            self.stdout.write(self.style.ERROR("A Liga no banco não tem api_id. Mapeie a liga primeiro."))
            return

        self.stdout.write(self.style.SUCCESS(f"\nBuscando times da temporada atual na API para a Liga: {db_league.name}"))

        # Determinar temporada atual
        from datetime import datetime
        now = datetime.now()
        season_year = now.year

        params = {'league': db_league.api_id, 'season': season_year}
        try:
            resp = api._make_request(f"{api_config['base_url']}/teams", headers=headers, params=params, timeout=15)
            api._increment_usage('api_football_1')
            if resp.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Erro ao buscar times: {resp.status_code}"))
                return
            
            data_json = resp.json()
            if 'errors' in data_json and data_json['errors']:
                self.stdout.write(self.style.ERROR(f"Erro da API: {data_json['errors']}"))
                return
                
            data = data_json.get('response', [])
            api_teams = []
            for item in data:
                api_teams.append({
                    'id': str(item['team']['id']),
                    'name': item['team']['name']
                })
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Exceção: {e}"))
            return

        db_teams = db_league.teams.filter(api_id__isnull=True)
        if not db_teams.exists():
            self.stdout.write(self.style.SUCCESS("Todos os times desta liga no banco já possuem api_id!"))
            return

        self.stdout.write(f"Encontrados {db_teams.count()} times no banco sem api_id. Iniciando fuzzy matching...\n")

        for db_t in db_teams:
            best_match = None
            best_score = 0
            
            for at in api_teams:
                # Compara db_t.name com at['name'] usando difflib
                score = difflib.SequenceMatcher(None, db_t.name.lower(), at['name'].lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = at

            if best_match and best_score > 0.65:
                db_t.api_id = best_match['id']
                db_t.save()
                self.stdout.write(self.style.SUCCESS(f"✅ Mapeado: Banco '{db_t.name}' -> API '{best_match['name']}' (ID: {best_match['id']}, Score: {best_score:.2f})"))
            else:
                self.stdout.write(self.style.WARNING(f"❌ Não mapeado com certeza: Banco '{db_t.name}'. Melhor match: '{best_match['name'] if best_match else 'Nenhum'}' (Score: {best_score:.2f})"))
