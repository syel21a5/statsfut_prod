import sys
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import Match, ScannerTip
from matches.services.advanced_stats import MatchAnalyzer

class Command(BaseCommand):
    help = 'Gera e salva as dicas do Scanner Inteligente no banco de dados para os próximos 3 dias.'

    def handle(self, *args, **options):
        br_tz = ZoneInfo('America/Sao_Paulo')
        now_br = timezone.now().astimezone(br_tz)
        start_of_day = now_br.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_of_day + timedelta(days=3) # Hoje, Amanhã, Depois de Amanhã
        
        matches = Match.objects.filter(
            date__range=(start_of_day, end_date),
            status__in=['NS', 'Not Started', 'Scheduled', 'TBD', 'POSTPONED', 'Postponed']
        ).select_related('home_team', 'away_team')

        self.stdout.write(f"Iniciando scan para {matches.count()} jogos não iniciados...")

        created_count = 0
        updated_count = 0

        def save_tip(match, market, probability, text):
            nonlocal created_count, updated_count
            _, created = ScannerTip.objects.update_or_create(
                match=match, market=market,
                defaults={'probability': probability, 'prediction_text': text}
            )
            if created: created_count += 1
            else: updated_count += 1

        for match in matches:
            try:
                analyzer = MatchAnalyzer(match)
                goals: dict = analyzer.get_goal_markets() or {}
                corners: dict = analyzer.get_corner_markets() or {}
                odds: dict = analyzer.get_match_odds_probs() or {}
                disciplinary: dict = analyzer.get_disciplinary_stats() or {}
                shots: dict = analyzer.get_shot_efficiency() or {}
                
                home = match.home_team.name
                away = match.away_team.name
                
                # ========== MERCADO DE GOLS ==========
                
                # HT Goal (>= 75%)
                if goals.get('ht_goal', 0) >= 75:
                    save_tip(match, 'HT_GOAL', goals['ht_goal'], 'Goal in 1st Half (HT)')
                
                # HT Goals Range Not 2-4 (Sim <= 30% -> Não >= 70%)
                if goals.get('bracket_1t_2_4') is not None and goals.get('bracket_1t_2_4') <= 30:
                    prob_not = 100 - goals['bracket_1t_2_4']
                    save_tip(match, 'HT_GOALS_NOT_2_4', prob_not, 'Not 2-4 Goals in 1st Half (HT)')
                
                # 2T Goals Range Not 2-4 (Sim <= 30% -> Não >= 70%)
                if goals.get('bracket_2t_2_4') is not None and goals.get('bracket_2t_2_4') <= 30:
                    prob_not = 100 - goals['bracket_2t_2_4']
                    save_tip(match, 'SH_GOALS_NOT_2_4', prob_not, 'Not 2-4 Goals in 2nd Half (2T)')
                
                # Double Chance + Under Goals Combo
                dc_unders = goals.get('dc_unders') or {}
                for combo in ['1X', 'X2']:
                    label_combo = f"{home} or Draw" if combo == '1X' else f"Draw or {away}"
                    for line in [2.5, 3.5, 4.5, 5.5]:
                        line_str = str(line).replace('.', '_')
                        key = f"{combo}_under_{line_str}"
                        prob = dc_unders.get(key, 0)
                        threshold = 70 if line == 2.5 else (75 if line == 3.5 else (80 if line == 4.5 else 85))
                        if prob >= threshold:
                            market_code = f"DC_{combo}_UNDER_{line_str}"
                            save_tip(match, market_code, prob, f"{label_combo} & Under {line} Goals")

                # Double Chance + Over Goals Combo
                dc_overs = goals.get('dc_overs') or {}
                for combo in ['1X', 'X2']:
                    label_combo = f"{home} or Draw" if combo == '1X' else f"Draw or {away}"
                    for line in [0.5, 1.5, 2.5, 3.5]:
                        line_str = str(line).replace('.', '_')
                        key = f"{combo}_over_{line_str}"
                        prob = dc_overs.get(key, 0)
                        threshold = 85 if line == 0.5 else (70 if line == 1.5 else (55 if line == 2.5 else 45))
                        if prob >= threshold:
                            market_code = f"DC_{combo}_OVER_{line_str}"
                            save_tip(match, market_code, prob, f"{label_combo} & Over {line} Goals")

                # Double Chance + BTTS Combo
                dc_btts = goals.get('dc_btts') or {}
                for combo in ['1X', 'X2']:
                    label_combo = f"{home} or Draw" if combo == '1X' else f"Draw or {away}"
                    for suffix in ['yes', 'no']:
                        key = f"{combo}_btts_{suffix}"
                        prob = dc_btts.get(key, 0)
                        threshold = 55 if suffix == 'yes' else 45
                        if prob >= threshold:
                            btts_label = "Both Teams to Score (Yes)" if suffix == 'yes' else "Both Teams to Score (No)"
                            market_code = f"DC_{combo}_BTTS_{suffix.upper()}"
                            save_tip(match, market_code, prob, f"{label_combo} & {btts_label}")
                
                # Over 0.5 (>= 90%)
                if goals.get('over_05', 0) >= 90:
                    save_tip(match, 'OVER_05', goals['over_05'], 'Over 0.5 Goals')
                
                # Over 1.5 (>= 80%)
                if goals.get('over_15', 0) >= 80:
                    save_tip(match, 'OVER_15', goals['over_15'], 'Over 1.5 Goals')
                    
                # Over 2.5 (>= 65%)
                if goals.get('over_25', 0) >= 65:
                    save_tip(match, 'OVER_25', goals['over_25'], 'Over 2.5 Goals')
                    
                # Over 3.5 (>= 50%)
                if goals.get('over_35', 0) >= 50:
                    save_tip(match, 'OVER_35', goals['over_35'], 'Over 3.5 Goals')
                    
                # Under 3.5 (>= 70%)
                if goals.get('under_35', 0) >= 70:
                    save_tip(match, 'UNDER_35', goals['under_35'], 'Under 3.5 Goals')
                    
                # Under 4.5 (>= 75%)
                if goals.get('under_45', 0) >= 75:
                    save_tip(match, 'UNDER_45', goals['under_45'], 'Under 4.5 Goals')
                    
                # Under 5.5 (>= 80%)
                if goals.get('under_55', 0) >= 80:
                    save_tip(match, 'UNDER_55', goals['under_55'], 'Under 5.5 Goals')
                    
                # Under 6.5 (>= 85%)
                if goals.get('under_65', 0) >= 85:
                    save_tip(match, 'UNDER_65', goals['under_65'], 'Under 6.5 Goals')
                    
                # BTTS (>= 65%)
                if goals.get('btts', 0) >= 65:
                    save_tip(match, 'BTTS', goals['btts'], 'Both Teams to Score')
                
                # BTTS 1st Half (>= 50%)
                if goals.get('btts_1h', 0) >= 50:
                    save_tip(match, 'BTTS_1H', goals['btts_1h'], 'BTTS 1st Half')
                
                # BTTS 2nd Half (>= 50%)
                if goals.get('btts_2h', 0) >= 50:
                    save_tip(match, 'BTTS_2H', goals['btts_2h'], 'BTTS 2nd Half')
                
                # BTTS Both Halves (>= 40%)
                if goals.get('btts_both', 0) >= 40:
                    save_tip(match, 'BTTS_BOTH', goals['btts_both'], 'BTTS Both Halves')
                
                # ========== VENCEDOR / RESULTADO ==========
                
                # Match Winner
                home_win = odds.get('home_win', 0)
                away_win = odds.get('away_win', 0)
                draw_prob = odds.get('draw', 0)
                
                if home_win >= 65:
                    save_tip(match, 'HOME_WIN', home_win, f'{home} to Win')
                elif away_win >= 65:
                    save_tip(match, 'AWAY_WIN', away_win, f'{away} to Win')
                
                # Double Chance 1X (>= 75%)
                dc_home = odds.get('double_home', 0)
                dc_away = odds.get('double_away', 0)
                if dc_home >= 75:
                    save_tip(match, 'DC_1X', dc_home, f'Double Chance 1X ({home} or Draw)')
                if dc_away >= 75:
                    save_tip(match, 'DC_X2', dc_away, f'Double Chance X2 (Draw or {away})')
                
                # Draw No Bet (>= 65%)
                dnb: dict = goals.get('dnb') or {}
                if dnb.get('home', 0) >= 65:
                    save_tip(match, 'DNB_HOME', dnb['home'], f'Draw No Bet - {home}')
                elif dnb.get('away', 0) >= 65:
                    save_tip(match, 'DNB_AWAY', dnb['away'], f'Draw No Bet - {away}')
                
                # First to Score (>= 75%)
                home_first = goals.get('home_first_score', 0)
                away_first = goals.get('away_first_score', 0)
                if home_first >= 75:
                    save_tip(match, 'FIRST_SCORE_HOME', home_first, f'{home} to Score First')
                elif away_first >= 75:
                    save_tip(match, 'FIRST_SCORE_AWAY', away_first, f'{away} to Score First')
                
                # HT Winner (>= 50%)
                ht_winner: dict = goals.get('ht_winner') or {}
                if ht_winner.get('home', 0) >= 50:
                    save_tip(match, 'HT_HOME_WIN', ht_winner['home'], f'{home} Leading at HT')
                elif ht_winner.get('away', 0) >= 50:
                    save_tip(match, 'HT_AWAY_WIN', ht_winner['away'], f'{away} Leading at HT')
                
                # ========== CLEAN SHEET / WIN TO NIL ==========
                
                home_special: dict = goals.get('home_special') or {}
                away_special: dict = goals.get('away_special') or {}
                
                if home_special.get('clean_sheet', 0) >= 50:
                    save_tip(match, 'HOME_CS', home_special['clean_sheet'], f'{home} Clean Sheet')
                if away_special.get('clean_sheet', 0) >= 50:
                    save_tip(match, 'AWAY_CS', away_special['clean_sheet'], f'{away} Clean Sheet')
                if home_special.get('win_to_nil', 0) >= 50:
                    save_tip(match, 'HOME_WTN', home_special['win_to_nil'], f'{home} Win to Nil')
                if away_special.get('win_to_nil', 0) >= 50:
                    save_tip(match, 'AWAY_WTN', away_special['win_to_nil'], f'{away} Win to Nil')
                
                # ========== HANDICAPS (>= 65%) ==========
                
                handicaps: dict = goals.get('handicaps') or {}
                if handicaps.get('home_minus_0_5', 0) >= 65:
                    save_tip(match, 'HC_HOME_M05', handicaps['home_minus_0_5'], f'{home} -0.5 (AH)')
                if handicaps.get('home_minus_1_5', 0) >= 50:
                    save_tip(match, 'HC_HOME_M15', handicaps['home_minus_1_5'], f'{home} -1.5 (AH)')
                if handicaps.get('away_plus_1_5', 0) >= 75:
                    save_tip(match, 'HC_AWAY_P15', handicaps['away_plus_1_5'], f'{away} +1.5 (AH)')
                
                # ========== WINNING MARGINS (>= 40%) ==========
                
                margins: dict = goals.get('winning_margins') or {}
                if margins.get('home_1', 0) >= 40:
                    save_tip(match, 'MARGIN_H1', margins['home_1'], f'{home} Wins by 1 Goal')
                if margins.get('home_2', 0) >= 30:
                    save_tip(match, 'MARGIN_H2', margins['home_2'], f'{home} Wins by 2 Goals')
                
                # ========== WINNER + BTTS COMBO (>= 40%) ==========
                
                wb: dict = goals.get('winner_btts') or {}
                if wb.get('home_yes', 0) >= 40:
                    save_tip(match, 'WIN_BTTS_HY', wb['home_yes'], f'{home} Win & BTTS Yes')
                if wb.get('away_yes', 0) >= 40:
                    save_tip(match, 'WIN_BTTS_AY', wb['away_yes'], f'{away} Win & BTTS Yes')
                if wb.get('home_no', 0) >= 40:
                    save_tip(match, 'WIN_BTTS_HN', wb['home_no'], f'{home} Win & BTTS No')
                    
                # ========== HALF WITH MOST GOALS (>= 55%) ==========
                
                hmg: dict = goals.get('half_most_goals') or {}
                if hmg.get('2t', 0) >= 55:
                    save_tip(match, 'MOST_2H', hmg['2t'], '2nd Half Most Goals')
                if hmg.get('1t', 0) >= 55:
                    save_tip(match, 'MOST_1H', hmg['1t'], '1st Half Most Goals')
                
                # ========== ESCANTEIOS (>= 65%) ==========
                
                if corners and corners.get('match_has_data'):
                    m_overs: dict = corners.get('match_overs') or {}
                    if m_overs.get(7, 0) >= 70:
                        save_tip(match, 'CORNERS_OVER_75', m_overs[7], 'Over 7.5 Corners')
                    if m_overs.get(8, 0) >= 70:
                        save_tip(match, 'CORNERS_OVER_85', m_overs[8], 'Over 8.5 Corners')
                    if m_overs.get(9, 0) >= 65:
                        save_tip(match, 'CORNERS_OVER_95', m_overs[9], 'Over 9.5 Corners')
                    if m_overs.get(10, 0) >= 60:
                        save_tip(match, 'CORNERS_OVER_105', m_overs[10], 'Over 10.5 Corners')
                    if m_overs.get(11, 0) >= 55:
                        save_tip(match, 'CORNERS_OVER_115', m_overs[11], 'Over 11.5 Corners')
                    
                    # Corner Winner (>= 60%)
                    wc: dict = corners.get('winner_corners') or {}
                    if wc.get('home', 0) >= 60:
                        save_tip(match, 'CORNER_WIN_H', wc['home'], f'{home} Wins Corners')
                    elif wc.get('away', 0) >= 60:
                        save_tip(match, 'CORNER_WIN_A', wc['away'], f'{away} Wins Corners')
                
                # ========== CARTÕES (>= 65%) ==========
                
                if disciplinary and disciplinary.get('match_has_data'):
                    cards_ou: dict = disciplinary.get('cards_totals_overs') or {}
                    if cards_ou.get(3, 0) >= 70:
                        save_tip(match, 'CARDS_OVER_35', cards_ou[3], 'Over 3.5 Cards')
                    if cards_ou.get(4, 0) >= 65:
                        save_tip(match, 'CARDS_OVER_45', cards_ou[4], 'Over 4.5 Cards')
                    if cards_ou.get(5, 0) >= 60:
                        save_tip(match, 'CARDS_OVER_55', cards_ou[5], 'Over 5.5 Cards')
                    if cards_ou.get(6, 0) >= 50:
                        save_tip(match, 'CARDS_OVER_65', cards_ou[6], 'Over 6.5 Cards')
                    
                    # Card Winner (>= 60%)
                    wk: dict = disciplinary.get('winner_cards') or {}
                    if wk.get('home', 0) >= 60:
                        save_tip(match, 'CARD_WIN_H', wk['home'], f'{home} Most Cards')
                    elif wk.get('away', 0) >= 60:
                        save_tip(match, 'CARD_WIN_A', wk['away'], f'{away} Most Cards')
                
                # ========== CHUTES (>= 65%) ==========
                
                if shots and shots.get('match_has_data'):
                    st_ou: dict = shots.get('shots_totals_overs') or {}
                    if st_ou.get(20, 0) >= 70:
                        save_tip(match, 'SHOTS_OVER_205', st_ou[20], 'Over 20.5 Total Shots')
                    if st_ou.get(22, 0) >= 65:
                        save_tip(match, 'SHOTS_OVER_225', st_ou[22], 'Over 22.5 Total Shots')
                    if st_ou.get(24, 0) >= 60:
                        save_tip(match, 'SHOTS_OVER_245', st_ou[24], 'Over 24.5 Total Shots')
                    
                    sot_ou: dict = shots.get('shots_on_target_overs') or {}
                    if sot_ou.get(6, 0) >= 70:
                        save_tip(match, 'SOT_OVER_65', sot_ou[6], 'Over 6.5 Shots on Target')
                    if sot_ou.get(7, 0) >= 65:
                        save_tip(match, 'SOT_OVER_75', sot_ou[7], 'Over 7.5 Shots on Target')
                    if sot_ou.get(8, 0) >= 60:
                        save_tip(match, 'SOT_OVER_85', sot_ou[8], 'Over 8.5 Shots on Target')
                    
                    # Shot Winner (>= 60%)
                    ws: dict = shots.get('winner_shots') or {}
                    if ws.get('home', 0) >= 60:
                        save_tip(match, 'SHOT_WIN_H', ws['home'], f'{home} More Shots')
                    elif ws.get('away', 0) >= 60:
                        save_tip(match, 'SHOT_WIN_A', ws['away'], f'{away} More Shots')

            except Exception as e:
                continue

        self.stdout.write(self.style.SUCCESS(f"Scanner finalizado! Criados: {created_count}, Atualizados: {updated_count}"))
