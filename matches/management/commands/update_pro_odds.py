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
    help = 'Busca fixtures futuras, odds pré-jogo e predictions da API-Football PRO'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=3, help='Dias a frente para buscar jogos')
        parser.add_argument('--league_id', type=int, default=None, help='ID da liga na API-Football (ex: 71 para Brasileirao)')

    def handle(self, *args, **options):
        days_ahead = options['days']
        league_id_filter = options['league_id']

        self.stdout.write(self.style.SUCCESS(f"Iniciando atualização PRO de Odds e Predictions ({days_ahead} dias)"))
        
        api = APIManager()
        api_config = api.apis.get('api_football_1')
        
        if not api_config or not api_config.get('key'):
            self.stdout.write(self.style.ERROR("Chave API_FOOTBALL_KEY não encontrada. Abortando."))
            return
            
        base_url = api_config['base_url']
        headers = api._get_headers(api_config)
        
        # Mapeamento interno das nossas ligas e os IDs da API-Football
        # Usaremos as ligas ativas no banco de dados que possuem mapeamento
        # (Idealmente você deve garantir que `api_manager.LEAGUE_MAPPINGS` ou o Model tenha esses IDs)
        
        target_leagues = []
        for l_name, l_data in api.LEAGUE_MAPPINGS.items():
            if l_data.get('api_football'):
                for api_id in l_data['api_football']:
                    if league_id_filter and api_id != league_id_filter:
                        continue
                        
                    # Find DB League
                    db_league = None
                    try:
                        # Busca pelo nome exato ou contenção segura
                        db_league = League.objects.filter(name__iexact=l_name).first()
                        if not db_league:
                            db_league = League.objects.filter(name__icontains=l_name).first()
                    except:
                        pass
                        
                    if db_league:
                        target_leagues.append({
                            'api_id': api_id,
                            'db_obj': db_league
                        })
                        
        if not target_leagues:
            self.stdout.write(self.style.WARNING("Nenhuma liga mapeada encontrada para a API-Football."))
            return

        today_str = datetime.now().strftime('%Y-%m-%d')
        future_str = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        season_year = datetime.now().year
        
        db_season, _ = Season.objects.get_or_create(year=season_year)

        updates = 0
        creations = 0

        for league_data in target_leagues:
            api_league_id = league_data['api_id']
            db_league = league_data['db_obj']
            
            self.stdout.write(f"\\n--> Buscando fixtures para a liga: {db_league.name} (API ID: {api_league_id})")
            
            url_fixtures = f"{base_url}/fixtures"
            params = {
                'league': api_league_id,
                'season': season_year,
                'from': today_str,
                'to': future_str
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
                    
                    home_name = fix['teams']['home']['name']
                    away_name = fix['teams']['away']['name']
                    
                    # Resolve times no DB
                    ht_obj = resolve_team(home_name, db_league)
                    at_obj = resolve_team(away_name, db_league)
                    
                    if not ht_obj:
                        ht_obj = Team.objects.create(name=home_name, league=db_league)
                        self.stdout.write(f"  [Time Criado] {home_name}")
                    
                    if not at_obj:
                        at_obj = Team.objects.create(name=away_name, league=db_league)
                        self.stdout.write(f"  [Time Criado] {away_name}")
                        
                    # Busca Match no DB (pelo time e data aproximada)
                    start_window = f_date - timedelta(hours=12)
                    end_window = f_date + timedelta(hours=12)
                    
                    match = Match.objects.filter(
                        league=db_league,
                        home_team=ht_obj,
                        away_team=at_obj,
                        date__range=(start_window, end_window)
                    ).first()
                    
                    # Salva ou cria
                    with transaction.atomic():
                        if not match:
                            match = Match.objects.create(
                                league=db_league,
                                season=db_season,
                                home_team=ht_obj,
                                away_team=at_obj,
                                date=f_date,
                                status='Scheduled' if f_status in ['NS', 'TBD'] else f_status,
                                api_id=str(f_id)
                            )
                            creations += 1
                        else:
                            if not match.api_id:
                                match.api_id = str(f_id)
                                match.save(update_fields=['api_id'])
                        
                        # --- PASSO 2: Buscar Odds ---
                        if match.status not in ['FT', 'AET', 'PEN', 'PST', 'CANC', 'FINISHED']:
                            self.stdout.write(f"  [Odds] Extraindo para {home_name} x {away_name}...")
                            odds_data = api.get_odds(f_id, bookmaker=8) # Bet365
                            time.sleep(0.5) # Anti-rate limit
                            
                            if odds_data and len(odds_data) > 0:
                                bookmakers = odds_data[0].get('bookmakers', [])
                                if bookmakers:
                                    markets = bookmakers[0].get('bets', [])
                                    
                                    for m in markets:
                                        m_id = m.get('id')
                                        vals = m.get('values', [])
                                        
                                        # Match Winner (ID 1)
                                        if m_id == 1:
                                            for v in vals:
                                                if str(v.get('value')) == 'Home': match.home_team_win_odds = float(v['odd'])
                                                elif str(v.get('value')) == 'Draw': match.draw_odds = float(v['odd'])
                                                elif str(v.get('value')) == 'Away': match.away_team_win_odds = float(v['odd'])
                                        
                                        # Goals Over/Under (ID 5)
                                        elif m_id == 5:
                                            for v in vals:
                                                if str(v.get('value')) == 'Over 1.5': match.over_15_odds = float(v['odd'])
                                                elif str(v.get('value')) == 'Over 2.5': match.over_25_odds = float(v['odd'])
                                                elif str(v.get('value')) == 'Under 2.5': match.under_25_odds = float(v['odd'])
                                                
                                        # BTTS (ID 8)
                                        elif m_id == 8:
                                            for v in vals:
                                                if str(v.get('value')) == 'Yes': match.btts_yes_odds = float(v['odd'])
                                                elif str(v.get('value')) == 'No': match.btts_no_odds = float(v['odd'])

                            # --- PASSO 3: Buscar Predictions Matemáticas ---
                            self.stdout.write(f"  [Pred] Inteligência Artificial...")
                            pred_data = api.get_predictions(f_id)
                            time.sleep(0.5)
                            
                            if pred_data and len(pred_data) > 0:
                                match.predictions_data = pred_data[0] # JSON Field com tudo mastigado
                                
                            match.save()
                            updates += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar liga {api_league_id}: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f"Concluído! {creations} criados, {updates} atualizados."))
