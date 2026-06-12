import os
import time
import requests
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from matches.models import Match, League, Team, Season
from matches.api_manager import APIManager
from matches.utils_odds_api import resolve_team

class Command(BaseCommand):
    help = 'Busca resultados recentes e extrai estatísticas profundas via API-Football PRO'

    def add_arguments(self, parser):
        parser.add_argument('--days_back', type=int, default=2, help='Dias para trás para buscar jogos finalizados')
        parser.add_argument('--league_id', type=int, default=None, help='ID da liga na API-Football (ex: 71)')

    def handle(self, *args, **options):
        days_back = options['days_back']
        league_id_filter = options['league_id']

        self.stdout.write(self.style.SUCCESS(f"Iniciando atualização PRO de Resultados e Stats ({days_back} dias p/ trás)"))
        
        api = APIManager()
        api_config = api.apis.get('api_football_1')
        
        if not api_config or not api_config.get('key'):
            self.stdout.write(self.style.ERROR("Chave API_FOOTBALL_KEY não encontrada. Abortando."))
            return
            
        base_url = api_config['base_url']
        headers = api._get_headers(api_config)
        
        target_leagues = []
        for l_name, l_data in api.LEAGUE_MAPPINGS.items():
            if l_data.get('api_football'):
                for api_id in l_data['api_football']:
                    if league_id_filter and api_id != league_id_filter:
                        continue
                        
                    db_league = League.objects.filter(name__icontains=l_name[:5]).first()
                    if db_league:
                        target_leagues.append({'api_id': api_id, 'db_obj': db_league})
                        
        if not target_leagues:
            self.stdout.write(self.style.WARNING("Nenhuma liga mapeada encontrada para a API-Football."))
            return

        past_str = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        today_str = datetime.now().strftime('%Y-%m-%d')
        season_year = datetime.now().year

        updates = 0
        stats_updates = 0

        for league_data in target_leagues:
            api_league_id = league_data['api_id']
            db_league = league_data['db_obj']
            
            self.stdout.write(f"\n--> Buscando resultados para: {db_league.name} (API ID: {api_league_id})")
            
            url_fixtures = f"{base_url}/fixtures"
            params = {
                'league': api_league_id,
                'season': season_year,
                'from': past_str,
                'to': today_str
            }
            
            try:
                resp = requests.get(url_fixtures, headers=headers, params=params, timeout=15)
                api._increment_usage('api_football_1')
                
                if resp.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"Erro na API para a liga {api_league_id}"))
                    continue
                    
                fixtures = resp.json().get('response', [])
                self.stdout.write(f"Encontrados {len(fixtures)} jogos na janela.")
                
                for fix in fixtures:
                    f_id = fix['fixture']['id']
                    f_date = datetime.fromisoformat(fix['fixture']['date'])
                    f_status = fix['fixture']['status']['short']
                    
                    # Somente jogos finalizados
                    if f_status not in ['FT', 'AET', 'PEN']:
                        continue
                        
                    home_name = fix['teams']['home']['name']
                    away_name = fix['teams']['away']['name']
                    home_score = fix['goals']['home']
                    away_score = fix['goals']['away']
                    
                    ht_obj = resolve_team(home_name, db_league)
                    at_obj = resolve_team(away_name, db_league)
                    
                    if not ht_obj:
                        ht_obj = Team.objects.create(name=home_name, league=db_league)
                        self.stdout.write(f"  [Time Criado] {home_name}")
                    
                    if not at_obj:
                        at_obj = Team.objects.create(name=away_name, league=db_league)
                        self.stdout.write(f"  [Time Criado] {away_name}")
                        
                    start_window = f_date - timedelta(hours=12)
                    end_window = f_date + timedelta(hours=12)
                    
                    match = Match.objects.filter(
                        league=db_league,
                        home_team=ht_obj,
                        away_team=at_obj,
                        date__range=(start_window, end_window)
                    ).first()
                    
                    if not match:
                        continue
                        
                    # Atualiza placar
                    updated = False
                    if match.status != 'Finished' or match.home_score != home_score or match.away_score != away_score:
                        match.status = 'Finished'
                        match.home_score = home_score
                        match.away_score = away_score
                        match.api_id = str(f_id)
                        updated = True

                    # Busca Estatisticas Profundas se nao houver escanteios registrados
                    if match.home_corners is None:
                        self.stdout.write(f"  [Stats] Buscando estatísticas profundas para {home_name} x {away_name}")
                        url_stats = f"{base_url}/fixtures/statistics"
                        resp_stats = requests.get(url_stats, headers=headers, params={'fixture': f_id}, timeout=10)
                        api._increment_usage('api_football_1')
                        time.sleep(0.5)
                        
                        if resp_stats.status_code == 200:
                            stats_data = resp_stats.json().get('response', [])
                            
                            home_stats_list = [s for s in stats_data if str(s['team']['id']) == str(fix['teams']['home']['id'])]
                            away_stats_list = [s for s in stats_data if str(s['team']['id']) == str(fix['teams']['away']['id'])]
                            
                            if home_stats_list and away_stats_list:
                                h_stats = home_stats_list[0]['statistics']
                                a_stats = away_stats_list[0]['statistics']
                                
                                def get_stat(stats_list, stat_type):
                                    for item in stats_list:
                                        if item['type'] == stat_type and item['value'] is not None:
                                            # Tratar porcentagem como "55%" para int
                                            val = item['value']
                                            if isinstance(val, str) and '%' in val:
                                                return int(val.replace('%', ''))
                                            return int(val)
                                    return 0
                                
                                match.home_corners = get_stat(h_stats, 'Corner Kicks')
                                match.away_corners = get_stat(a_stats, 'Corner Kicks')
                                match.home_shots = get_stat(h_stats, 'Total Shots')
                                match.away_shots = get_stat(a_stats, 'Total Shots')
                                match.home_shots_on_target = get_stat(h_stats, 'Shots on Goal')
                                match.away_shots_on_target = get_stat(a_stats, 'Shots on Goal')
                                match.home_fouls = get_stat(h_stats, 'Fouls')
                                match.away_fouls = get_stat(a_stats, 'Fouls')
                                match.home_yellow = get_stat(h_stats, 'Yellow Cards')
                                match.away_yellow = get_stat(a_stats, 'Yellow Cards')
                                match.home_red = get_stat(h_stats, 'Red Cards')
                                match.away_red = get_stat(a_stats, 'Red Cards')
                                updated = True
                                stats_updates += 1
                                
                    if updated:
                        match.save()
                        updates += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar liga {api_league_id}: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f"Concluído! {updates} jogos atualizados ({stats_updates} receberam estatísticas profundas)."))
