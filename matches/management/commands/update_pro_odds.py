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
                            
                            # Tenta Bet365 primeiro, fallback para qualquer bookmaker
                            odds_data = api.get_odds(f_id, bookmaker=8)  # Bet365
                            time.sleep(0.5)
                            
                            chosen_bk_name = None
                            markets = []
                            
                            if odds_data and len(odds_data) > 0:
                                bookmakers = odds_data[0].get('bookmakers', [])
                                if bookmakers:
                                    chosen_bk_name = bookmakers[0].get('name', 'Bet365')
                                    markets = bookmakers[0].get('bets', [])
                            
                            # Fallback: se Bet365 não tem dados, busca sem filtro
                            if not markets:
                                self.stdout.write(f"    ⚠ Bet365 sem dados, tentando outros bookmakers...")
                                odds_data_all = api.get_odds(f_id, bookmaker=None)
                                time.sleep(0.5)
                                
                                if odds_data_all and len(odds_data_all) > 0:
                                    all_bks = odds_data_all[0].get('bookmakers', [])
                                    # Prioridade: Bet365 > Betano > 1xBet > qualquer
                                    preferred_ids = [8, 32, 11]
                                    chosen_bk = None
                                    for pref_id in preferred_ids:
                                        for bk in all_bks:
                                            if bk.get('id') == pref_id:
                                                chosen_bk = bk
                                                break
                                        if chosen_bk:
                                            break
                                    if not chosen_bk and all_bks:
                                        # Pega o bookmaker com mais mercados
                                        chosen_bk = max(all_bks, key=lambda b: len(b.get('bets', [])))
                                    
                                    if chosen_bk:
                                        chosen_bk_name = chosen_bk.get('name', '?')
                                        markets = chosen_bk.get('bets', [])
                            
                            odds_count = 0
                            
                            if markets:
                                self.stdout.write(f"    ✓ Usando {chosen_bk_name} ({len(markets)} mercados)")
                                
                                for m in markets:
                                    m_id = m.get('id')
                                    vals = m.get('values', [])
                                    
                                    # Helper para buscar valor por nome
                                    def get_odd(value_name):
                                        for v in vals:
                                            if str(v.get('value')) == value_name:
                                                return float(v['odd'])
                                        return None
                                    
                                    # === MERCADO 1: Match Winner (1x2) ===
                                    if m_id == 1:
                                        match.home_team_win_odds = get_odd('Home')
                                        match.draw_odds = get_odd('Draw')
                                        match.away_team_win_odds = get_odd('Away')
                                        odds_count += 3
                                    
                                    # === MERCADO 5: Goals Over/Under (Full Time) ===
                                    elif m_id == 5:
                                        match.over_15_odds = get_odd('Over 1.5')
                                        match.over_25_odds = get_odd('Over 2.5')
                                        match.over_35_odds = get_odd('Over 3.5')
                                        match.over_45_odds = get_odd('Over 4.5')
                                        match.over_55_odds = get_odd('Over 5.5')
                                        match.under_25_odds = get_odd('Under 2.5')
                                        match.under_35_odds = get_odd('Under 3.5')
                                        match.under_45_odds = get_odd('Under 4.5')
                                        match.under_55_odds = get_odd('Under 5.5')
                                        odds_count += 9
                                    
                                    # === MERCADO 6: Goals Over/Under 1st Half ===
                                    elif m_id == 6:
                                        match.ht_goal_odds = get_odd('Over 0.5')
                                        odds_count += 1
                                    
                                    # === MERCADO 8: Both Teams Score ===
                                    elif m_id == 8:
                                        match.btts_yes_odds = get_odd('Yes')
                                        match.btts_no_odds = get_odd('No')
                                        odds_count += 2
                                    
                                    # === MERCADO 12: Double Chance ===
                                    elif m_id == 12:
                                        match.dc_1x_odds = get_odd('Home/Draw')
                                        match.dc_x2_odds = get_odd('Draw/Away')
                                        odds_count += 2
                                    
                                    # === MERCADO 27: Clean Sheet - Home ===
                                    elif m_id == 27:
                                        match.clean_sheet_home_odds = get_odd('Yes')
                                        odds_count += 1
                                    
                                    # === MERCADO 28: Clean Sheet - Away ===
                                    elif m_id == 28:
                                        match.clean_sheet_away_odds = get_odd('Yes')
                                        odds_count += 1
                                    
                                    # === MERCADO 2: Home/Away (Draw No Bet) ===
                                    elif m_id == 2:
                                        match.dnb_home_odds = get_odd('Home')
                                        match.dnb_away_odds = get_odd('Away')
                                        odds_count += 2
                                    
                                    # === MERCADO 45: Corners Over/Under ===
                                    elif m_id == 45:
                                        for v in vals:
                                            val_str = str(v.get('value', ''))
                                            odd_val = float(v['odd'])
                                            if val_str == 'Over 6.5': match.corners_over_65_odds = odd_val
                                            elif val_str == 'Over 7.5': match.corners_over_75_odds = odd_val
                                            elif val_str == 'Over 8.5': match.corners_over_85_odds = odd_val
                                            elif val_str == 'Over 9.5': match.corners_over_95_odds = odd_val
                                            elif val_str == 'Over 10.5': match.corners_over_105_odds = odd_val
                                            elif val_str == 'Over 11.5': match.corners_over_115_odds = odd_val
                                        odds_count += 6
                                    
                                    # === MERCADO 55: Corners 1x2 ===
                                    elif m_id == 55:
                                        match.corners_home_win_odds = get_odd('Home')
                                        match.corners_draw_odds = get_odd('Draw')
                                        match.corners_away_win_odds = get_odd('Away')
                                        odds_count += 3
                                
                                self.stdout.write(f"    ✓ {odds_count} campos de odds preenchidos")
                            else:
                                self.stdout.write(f"    ✗ Nenhum bookmaker com odds disponíveis")

                            # --- PASSO 3: Buscar Predictions Matemáticas ---
                            self.stdout.write(f"  [Pred] Inteligência Artificial...")
                            pred_data = api.get_predictions(f_id)
                            time.sleep(0.5)
                            
                            if pred_data and len(pred_data) > 0:
                                match.predictions_data = pred_data[0]
                                
                            match.save()
                            updates += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar liga {api_league_id}: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f"Concluído! {creations} criados, {updates} atualizados."))
