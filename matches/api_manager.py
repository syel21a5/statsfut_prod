import os
import requests
import random
from datetime import datetime, timedelta
from django.core.cache import cache

class APIManager:
    """
    Gerenciador inteligente de múltiplas APIs de futebol
    Faz rotação automática e fallback entre APIs
    """
    
    LEAGUE_MAPPINGS = {
        'Premier League': {'api_football': [39], 'football_data': [2021]},
        'La Liga': {'api_football': [140], 'football_data': [2014]},
        'Bundesliga': {'api_football': [78], 'football_data': [2002]},
        'Serie A': {'api_football': [135], 'football_data': [2019]},
        'Ligue 1': {'api_football': [61], 'football_data': [2015]},
        'Brasileirao': {'api_football': [71], 'football_data': [2013]},
        'Superliga': {'api_football': [119], 'football_data': []},          # Dinamarca
        'Pro League': {'api_football': [144], 'football_data': []},
        'Liga Profesional': {'api_football': [128], 'football_data': []},    # Argentina
        # Extra top leagues (Football-Data supports some; else use API-Football by country)
        'Primeira Liga': {'api_football': [], 'football_data': [2017]},      # Portugal
        'Eredivisie': {'api_football': [], 'football_data': [2003]},         # Netherlands
        'Super Lig': {'api_football': [], 'football_data': [2018]},          # Turkey
    }

    COUNTRY_TOP_LEAGUES = {
        'England': ['Premier League'],
        'Spain': ['La Liga'],
        'Germany': ['Bundesliga'],
        'Italy': ['Serie A'],
        'France': ['Ligue 1'],
        'Belgium': ['Pro League', 'First Division A', 'Jupiler Pro League'],
        'Brazil': ['Brasileirão Série A', 'Serie A'],
        'Portugal': ['Primeira Liga'],
        'Netherlands': ['Eredivisie'],
        'Turkey': ['Super Lig', 'Süper Lig'],
        'Argentina': ['Liga Profesional'],
        'Greece': ['Super League 1', 'Super League'],
        'Austria': ['Bundesliga', 'Austrian Bundesliga'],
        'Switzerland': ['Super League', 'Swiss Super League'],
        'Czech Republic': ['Czech Liga', 'Fortuna Liga'],
        'Denmark': ['Superliga', 'Superligaen'],
        'Finland': ['Veikkausliiga'],
        'Norway': ['Eliteserien'],
        'Sweden': ['Allsvenskan'],
        'Poland': ['Ekstraklasa'],
        'Ukraine': ['Premier League'],
        'Argentina': ['Liga Profesional', 'Primera Division'],
        'Australia': ['A-League'],
        'Japan': ['J1 League'],
    }

    def __init__(self):
        self.apis = {
            'football_data_1': {
                'name': 'Football-Data.org #1 (Main)',
                'key': os.getenv('FOOTBALL_DATA_KEY'),
                'base_url': 'https://api.football-data.org/v4',
                'daily_limit': 1000, 
                'type': 'football_data'
            },
            'football_data_2': {
                'name': 'Football-Data.org #2 (vand)',
                'key': os.getenv('FOOTBALL_DATA_KEY_2'),
                'base_url': 'https://api.football-data.org/v4',
                'daily_limit': 1000,
                'type': 'football_data'
            },
            'football_data_3': {
                'name': 'Football-Data.org #3 (syel21a)',
                'key': os.getenv('FOOTBALL_DATA_KEY_3'),
                'base_url': 'https://api.football-data.org/v4',
                'daily_limit': 1000,
                'type': 'football_data'
            },
            'football_data_4': {
                'name': 'Football-Data.org #4 (divertema)',
                'key': os.getenv('FOOTBALL_DATA_KEY_4'),
                'base_url': 'https://api.football-data.org/v4',
                'daily_limit': 1000,
                'type': 'football_data'
            },
            'football_data_5': {
                'name': 'Football-Data.org #5 (discipulo)',
                'key': os.getenv('FOOTBALL_DATA_KEY_5'),
                'base_url': 'https://api.football-data.org/v4',
                'daily_limit': 1000,
                'type': 'football_data'
            },
            'football_data_6': {
                'name': 'Football-Data.org #6 (ofertas)',
                'key': os.getenv('FOOTBALL_DATA_KEY_6'),
                'base_url': 'https://api.football-data.org/v4',
                'daily_limit': 1000,
                'type': 'football_data'
            },
            'football_data_7': {
                'name': 'Football-Data.org #7 (adm1)',
                'key': os.getenv('FOOTBALL_DATA_KEY_7'),
                'base_url': 'https://api.football-data.org/v4',
                'daily_limit': 1000,
                'type': 'football_data'
            },
            'football_data_8': {
                'name': 'Football-Data.org #8 (adm2)',
                'key': os.getenv('FOOTBALL_DATA_KEY_8'),
                'base_url': 'https://api.football-data.org/v4',
                'daily_limit': 1000,
                'type': 'football_data'
            },
            'api_football_1': {
                'name': 'API-Football #1 (syel21)',
                'key': os.getenv('API_FOOTBALL_KEY_1'),
                'base_url': 'https://v3.football.api-sports.io',
                'daily_limit': 100,
                'type': 'api_football'
            },
            'api_football_2': {
                'name': 'API-Football #2 (eletr)',
                'key': os.getenv('API_FOOTBALL_KEY_2'),
                'base_url': 'https://v3.football.api-sports.io',
                'daily_limit': 100,
                'type': 'api_football'
            }
        }
    
    def _get_usage_count(self, api_id):
        """Retorna quantas requests foram feitas hoje nessa API"""
        cache_key = f'api_usage_{api_id}_{datetime.now().date()}'
        return cache.get(cache_key, 0)
    
    def _increment_usage(self, api_id):
        """Incrementa contador de uso da API"""
        cache_key = f'api_usage_{api_id}_{datetime.now().date()}'
        current = cache.get(cache_key, 0)
        # Expira à meia-noite
        seconds_until_midnight = (datetime.now().replace(hour=23, minute=59, second=59) - datetime.now()).seconds
        cache.set(cache_key, current + 1, timeout=seconds_until_midnight)
    
    def _choose_best_api(self, exclude_apis=None):
        """Escolhe a API com mais créditos disponíveis"""
        best_api = None
        max_available = -1
        exclude_apis = exclude_apis or []
        
        for api_id, api_config in self.apis.items():
            if api_id in exclude_apis:
                continue
            if not api_config.get('key'):
                continue
                
            used = self._get_usage_count(api_id)
            available = api_config['daily_limit'] - used
            
            if available > max_available:
                max_available = available
                best_api = api_id
        
        return best_api if max_available > 0 else None
    
    def _choose_best_api_from_list(self, api_ids, exclude_apis=None):
        """Escolhe a melhor API dentre uma lista específica, respeitando limites diários"""
        exclude_apis = set(exclude_apis or [])
        best_api = None
        max_available = -1
        
        for api_id in api_ids:
            if api_id in exclude_apis:
                continue
            api_config = self.apis.get(api_id)
            if not api_config:
                continue
            if not api_config.get('key'):
                continue
            
            used = self._get_usage_count(api_id)
            available = api_config['daily_limit'] - used
            
            if available > max_available and available > 0:
                max_available = available
                best_api = api_id
        
        return best_api
    
    def get_live_fixtures(self, league_ids=None, exclude_apis=None):
        """
        Busca fixtures ao vivo
        """
        exclude_apis = exclude_apis or []
        fd_keys = [f'football_data_{i}' for i in range(1, 9)]
        api_fd = self._choose_best_api_from_list(fd_keys, exclude_apis=exclude_apis)
        if api_fd:
            api_config = self.apis[api_fd]
            try:
                print(f"[APIManager] Live fixtures via {api_fd} ({api_config['name']})")
                fixtures = self._get_football_data_fixtures(api_fd, api_config, status='live')
                if fixtures:
                    return fixtures
            except Exception as e:
                print(f"Erro na {api_config['name']}: {e}")
                exclude_apis.append(api_fd)
        
        af_keys = [f'api_football_{i}' for i in range(1, 3)]
        api_af = self._choose_best_api_from_list(af_keys, exclude_apis=exclude_apis)
        if not api_af:
            raise Exception("Todas as APIs atingiram o limite diário ou falharam!")
        
        api_config = self.apis[api_af]
        print(f"[APIManager] Live fixtures via {api_af} ({api_config['name']})")
        return self._get_api_football_fixtures(api_af, api_config, status='live', league_ids=league_ids)
    
    def get_upcoming_fixtures(self, league_ids=None, days_ahead=7, exclude_apis=None, league_name=None):
        """Busca próximos jogos (próximos X dias)"""
        exclude_apis = exclude_apis or []
        
        fd_ids = []
        af_ids = league_ids or []
        
        if league_name and league_name in self.LEAGUE_MAPPINGS:
            mapping = self.LEAGUE_MAPPINGS[league_name]
            fd_ids = mapping['football_data']
            if not af_ids:
                af_ids = mapping['api_football']
        
        fd_keys = [f'football_data_{i}' for i in range(1, 9)]

        # Só tenta Football-Data se houver IDs configurados para essa liga.
        # Para ligas apenas da API-Football (como Pro League), pulamos direto para a API-Football.
        if fd_ids:
            api_fd = self._choose_best_api_from_list(fd_keys, exclude_apis=exclude_apis)
            if api_fd:
                api_config = self.apis[api_fd]
                try:
                    print(f"[APIManager] Upcoming fixtures via {api_fd} ({api_config['name']})")
                    fixtures = self._get_football_data_fixtures(
                        api_fd,
                        api_config,
                        status='scheduled',
                        days_ahead=days_ahead,
                        league_ids=fd_ids,
                    )
                    if fixtures:
                        return fixtures
                except Exception as e:
                    print(f"Erro na {api_config['name']}: {e}")
                    exclude_apis.append(api_fd)
        
        af_keys = [f'api_football_{i}' for i in range(1, 3)]
        api_af = self._choose_best_api_from_list(af_keys, exclude_apis=exclude_apis)
        if not api_af:
            raise Exception("Todas as APIs atingiram o limite diário ou falharam!")
        
        api_config = self.apis[api_af]
        print(f"[APIManager] Upcoming fixtures via {api_af} ({api_config['name']})")
        return self._get_api_football_fixtures(api_af, api_config, status='scheduled', league_ids=af_ids, days_ahead=days_ahead)

    def get_upcoming_fixtures_by_country(self, country, days_ahead=7, exclude_apis=None):
        """
        Busca próximos jogos para a principal liga de um país automaticamente (API-Football).
        """
        exclude_apis = exclude_apis or []
        af_keys = [f'api_football_{i}' for i in range(1, 3)]
        api_af = self._choose_best_api_from_list(af_keys, exclude_apis=exclude_apis)
        if not api_af:
            raise Exception("APIs indisponíveis para busca por país.")
        api_config = self.apis[api_af]

        # Tenta recuperar IDs do cache para economizar requisições
        cache_key = f'league_ids_by_country_{country}'
        league_ids = cache.get(cache_key)

        if not league_ids:
            headers = {
                'x-rapidapi-host': 'v3.football.api-sports.io',
                'x-rapidapi-key': api_config['key']
            }
            # Descobre ligas do país
            params = {'country': country, 'type': 'League'}
            try:
                resp = requests.get(f"{api_config['base_url']}/leagues", headers=headers, params=params, timeout=10)
                self._increment_usage(api_af)
                if resp.status_code != 200:
                    raise Exception(f"Falha ao listar ligas do país {country}: {resp.status_code}")
                data = resp.json().get('response', [])

                wanted_names = self.COUNTRY_TOP_LEAGUES.get(country, [])
                league_ids = []
                for item in data:
                    lg = item.get('league', {})
                    seasons = item.get('seasons', [])
                    # Seleciona apenas temporada atual
                    has_current = any(s.get('current') for s in seasons)
                    if not has_current:
                        continue
                    name = lg.get('name')
                    if wanted_names and name not in wanted_names:
                        continue
                    league_ids.append(lg.get('id'))

                # fallback: se não achou por nome, pega a primeira liga atual
                if not league_ids and data:
                    for item in data:
                        if any(s.get('current') for s in item.get('seasons', [])):
                            league_ids.append(item['league']['id'])
                            break
                
                # Cacheia por 30 dias se encontrou
                if league_ids:
                    cache.set(cache_key, league_ids, timeout=60*60*24*30)

            except Exception as e:
                print(f"Erro ao buscar ligas de {country}: {e}")
                return []

        if not league_ids:
            return []

        return self._get_api_football_fixtures(api_af, api_config, status='scheduled', league_ids=league_ids, days_ahead=days_ahead)
    
    def get_league_season_fixtures(self, league_id, season_year, exclude_apis=None):
        """
        Busca todos os jogos de uma liga em uma temporada específica.
        Usado para checar consistência de resultados em lote.
        """
        exclude_apis = exclude_apis or []
        fd_keys = [f'football_data_{i}' for i in range(1, 9)]
        api_id = self._choose_best_api_from_list(fd_keys, exclude_apis=exclude_apis)
        
        if not api_id:
            raise Exception("Todas as APIs atingiram o limite diário ou falharam para busca de temporada.")
        
        api_config = self.apis[api_id]
        headers = {'X-Auth-Token': api_config['key']}
        url = f"{api_config['base_url']}/competitions/{league_id}/matches"

        api_season_year = season_year
        european_multi_year = {2021}
        if league_id in european_multi_year:
            api_season_year = season_year - 1

        params = {'season': api_season_year}
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        self._increment_usage(api_id)
        
        if response.status_code == 404:
            print(f"Football-Data ainda não possui dados para league={league_id}, season={api_season_year}")
            return []
        
        if response.status_code != 200:
            raise Exception(f"Football-Data retornou status {response.status_code}: {response.text}")
        
        data = response.json()
        fixtures = data.get('matches', [])
        return self._normalize_football_data(fixtures)
    
    def _get_api_football_fixtures(self, api_id, api_config, status='live', league_ids=None, days_ahead=7):
        """Busca fixtures da API-Football"""
        headers = {
            'x-rapidapi-host': 'v3.football.api-sports.io',
            'x-rapidapi-key': api_config['key']
        }
        
        params = {}
        
        if status == 'live':
            params['live'] = 'all'
        else:
            # Próximos jogos
            date_from = datetime.now().date()
            date_to = date_from + timedelta(days=days_ahead)
            params['from'] = date_from.isoformat()
            params['to'] = date_to.isoformat()
        
        if league_ids:
            # Faz uma request por liga para economizar
            all_fixtures = []
            now = datetime.now()
            european_multi_year = {39, 140, 78, 135, 61, 144}
            for league_id in league_ids:
                params['league'] = league_id
                if league_id in european_multi_year:
                    season = now.year if now.month >= 7 else now.year - 1
                else:
                    season = now.year
                params['season'] = season
                
                response = requests.get(
                    f"{api_config['base_url']}/fixtures",
                    headers=headers,
                    params=params,
                    timeout=10
                )
                self._increment_usage(api_id)
                
                if response.status_code == 200:
                    data = response.json()
                    all_fixtures.extend(data.get('response', []))
            
            return self._normalize_api_football_data(all_fixtures)
        else:
            response = requests.get(
                f"{api_config['base_url']}/fixtures",
                headers=headers,
                params=params,
                timeout=10
            )
            self._increment_usage(api_id)
            
            if response.status_code == 200:
                data = response.json()
                return self._normalize_api_football_data(data.get('response', []))
            else:
                raise Exception(f"API retornou status {response.status_code}")
    
    def _get_football_data_fixtures(self, api_id, api_config, status='live', days_ahead=7, league_ids=None):
        """Busca fixtures da Football-Data.org"""
        headers = {
            'X-Auth-Token': api_config['key']
        }
        
        # Football-Data usa IDs diferentes: PL=2021, Brasileirão=2013
        # Se league_ids for fornecido, usa-o. Senão, usa todos os mapeados
        if league_ids:
            competitions = league_ids
        else:
            competitions = []
            for m in self.LEAGUE_MAPPINGS.values():
                competitions.extend(m['football_data'])
        
        all_fixtures = []
        
        for comp_id in competitions:
            params = {}
            if status != 'live':
                date_from = datetime.now().date()
                date_to = date_from + timedelta(days=days_ahead)
                params['dateFrom'] = date_from.isoformat()
                params['dateTo'] = date_to.isoformat()
        
            response = requests.get(
                f"{api_config['base_url']}/competitions/{comp_id}/matches",
                headers=headers,
                params=params,
                timeout=10
            )
            self._increment_usage(api_id)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                
                if status == 'live':
                    matches = [m for m in matches if m['status'] == 'IN_PLAY']
                
                all_fixtures.extend(matches)
        
        return self._normalize_football_data(all_fixtures)
    
    def _normalize_api_football_data(self, fixtures):
        """Normaliza dados da API-Football para formato padrão"""
        normalized = []
        
        for fixture in fixtures:
            normalized.append({
                'id': fixture['fixture']['id'],
                'date': fixture['fixture']['date'],
                'status': fixture['fixture']['status']['short'],
                'league': fixture['league']['name'],
                'country': fixture['league'].get('country'),
                'home_team': fixture['teams']['home']['name'],
                'away_team': fixture['teams']['away']['name'],
                'home_team_id': fixture['teams']['home']['id'],
                'away_team_id': fixture['teams']['away']['id'],
                'home_score': fixture['goals']['home'],
                'away_score': fixture['goals']['away'],
                'elapsed': fixture['fixture']['status'].get('elapsed'),
            })
        
        return normalized
    
    def _normalize_football_data(self, matches):
        """Normaliza dados da Football-Data.org para formato padrão"""
        normalized = []
        
        for match in matches:
            normalized.append({
                'id': match['id'],
                'date': match['utcDate'],
                'status': match['status'],
                'league': match['competition']['name'],
                'country': match.get('area', {}).get('name'),
                'home_team': match['homeTeam']['name'],
                'away_team': match['awayTeam']['name'],
                'home_team_id': match['homeTeam']['id'],
                'away_team_id': match['awayTeam']['id'],
                'home_score': match['score']['fullTime']['home'],
                'away_score': match['score']['fullTime']['away'],
                'elapsed': None,  # Football-Data não fornece minuto
            })
        
        return normalized
    def get_predictions(self, fixture_id):
        """Predições via API-Football desativadas"""
        return None

    def get_h2h(self, team1_name, team2_name):
        """
        Busca H2H entre dois times.
        Nota: A API pede IDs, mas como não temos o mapping exato sempre, 
        vamos tentar buscar pelo nome ou idealmente salvar o ID da API no time.
        Por enquanto, vamos simular ou buscar fixtures passadas se tivermos o ID.
        """
        # TODO: Implementar busca real de H2H quando tivermos IDs mapeados
        return []
