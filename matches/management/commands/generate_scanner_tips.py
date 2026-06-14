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
        end_date = start_of_day + timedelta(days=8) # Próximos 8 dias
        
        matches = Match.objects.filter(
            date__range=(start_of_day, end_date),
            status__in=['NS', 'Not Started', 'Scheduled', 'TBD', 'POSTPONED', 'Postponed']
        ).select_related('home_team', 'away_team')

        self.stdout.write(f"Iniciando scan para {matches.count()} jogos não iniciados...")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        def save_tip(match, market, probability, text):
            nonlocal created_count, updated_count
            _, created = ScannerTip.objects.update_or_create(
                match=match, market=market,
                defaults={'probability': probability, 'prediction_text': text}
            )
            if created: created_count += 1
            else: updated_count += 1

        for match in matches:
            diff_days = (match.date.astimezone(br_tz).date() - now_br.date()).days
            if diff_days >= 2:
                if ScannerTip.objects.filter(match=match).exists():
                    skipped_count += 1
                    continue

            try:
                analyzer = MatchAnalyzer(match)
                
                # Filtro de amostra mínima
                if len(analyzer.home_last_10) < 6 or len(analyzer.away_last_10) < 6:
                    continue

                goals: dict = analyzer.get_goal_markets() or {}
                corners: dict = analyzer.get_corner_markets() or {}
                odds: dict = analyzer.get_match_odds_probs() or {}
                
                home = match.home_team.name
                away = match.away_team.name
                
                # Probabilidades individuais para concordância
                home_len = len(analyzer.home_last_10)
                away_len = len(analyzer.away_last_10)
                
                home_over25_pct = int((sum(1 for m in analyzer.home_last_10 if m.home_score is not None and (m.home_score + m.away_score) > 2.5) / home_len) * 100) if home_len > 0 else 0
                away_over25_pct = int((sum(1 for m in analyzer.away_last_10 if m.home_score is not None and (m.home_score + m.away_score) > 2.5) / away_len) * 100) if away_len > 0 else 0

                home_over35_pct = int((sum(1 for m in analyzer.home_last_10 if m.home_score is not None and (m.home_score + m.away_score) > 3.5) / home_len) * 100) if home_len > 0 else 0
                away_over35_pct = int((sum(1 for m in analyzer.away_last_10 if m.home_score is not None and (m.home_score + m.away_score) > 3.5) / away_len) * 100) if away_len > 0 else 0

                home_btts_pct = int((sum(1 for m in analyzer.home_last_10 if m.home_score is not None and m.home_score > 0 and m.away_score > 0) / home_len) * 100) if home_len > 0 else 0
                away_btts_pct = int((sum(1 for m in analyzer.away_last_10 if m.home_score is not None and m.home_score > 0 and m.away_score > 0) / away_len) * 100) if away_len > 0 else 0

                # ========== MERCADO DE GOLS ==========
                if goals.get('ht_goal', 0) >= 85:
                    save_tip(match, 'HT_GOAL', goals['ht_goal'], 'Goal in 1st Half (HT)')
                
                dc_unders = goals.get('dc_unders') or {}
                for combo in ['1X', 'X2']:
                    label_combo = f"{home} or Draw" if combo == '1X' else f"Draw or {away}"
                    for line in [2.5, 3.5, 4.5, 5.5]:
                        line_str = str(line).replace('.', '_')
                        key = f"{combo}_under_{line_str}"
                        prob = dc_unders.get(key, 0)
                        threshold = 80 if line == 2.5 else (85 if line == 3.5 else 90)
                        if prob >= threshold:
                            save_tip(match, f"DC_{combo}_UNDER_{line_str}", prob, f"{label_combo} & Under {line} Goals")

                dc_overs = goals.get('dc_overs') or {}
                for combo in ['1X', 'X2']:
                    label_combo = f"{home} or Draw" if combo == '1X' else f"Draw or {away}"
                    for line in [1.5]:
                        line_str = str(line).replace('.', '_')
                        key = f"{combo}_over_{line_str}"
                        prob = dc_overs.get(key, 0)
                        threshold = 80
                        if prob >= threshold:
                            save_tip(match, f"DC_{combo}_OVER_{line_str}", prob, f"{label_combo} & Over {line} Goals")

                dc_btts = goals.get('dc_btts') or {}
                for combo in ['1X', 'X2']:
                    label_combo = f"{home} or Draw" if combo == '1X' else f"Draw or {away}"
                    for btts_val, label_btts in [('yes', 'Yes'), ('no', 'No')]:
                        key = f"{combo}_btts_{btts_val}"
                        prob = dc_btts.get(key, 0)
                        threshold = 70 if btts_val == 'no' else 65
                        if prob >= threshold:
                            save_tip(match, f"DC_{combo}_BTTS_{btts_val.upper()}", prob, f"{label_combo} & BTTS: {label_btts}")


                if goals.get('over_15', 0) >= 88:
                    save_tip(match, 'OVER_15', goals['over_15'], 'Over 1.5 Goals')
                if goals.get('over_25', 0) >= 80 and home_over25_pct >= 70 and away_over25_pct >= 70:
                    save_tip(match, 'OVER_25', goals['over_25'], 'Over 2.5 Goals')
                if goals.get('over_35', 0) >= 75 and home_over35_pct >= 60 and away_over35_pct >= 60:
                    save_tip(match, 'OVER_35', goals['over_35'], 'Over 3.5 Goals')
                if goals.get('under_35', 0) >= 85:
                    save_tip(match, 'UNDER_35', goals['under_35'], 'Under 3.5 Goals')
                if goals.get('under_45', 0) >= 90:
                    save_tip(match, 'UNDER_45', goals['under_45'], 'Under 4.5 Goals')

                    
                if goals.get('btts', 0) >= 80 and home_btts_pct >= 70 and away_btts_pct >= 70:
                    save_tip(match, 'BTTS', goals['btts'], 'Both Teams to Score')
                
                # ========== VENCEDOR / RESULTADO ==========
                if odds.get('home_win', 0) >= 75:
                    save_tip(match, 'HOME_WIN', odds['home_win'], f'{home} to Win')
                elif odds.get('away_win', 0) >= 75:
                    save_tip(match, 'AWAY_WIN', odds['away_win'], f'{away} to Win')
                
                if odds.get('double_home', 0) >= 90:
                    save_tip(match, 'DC_1X', odds['double_home'], f'Double Chance 1X ({home} or Draw)')
                if odds.get('double_away', 0) >= 90:
                    save_tip(match, 'DC_X2', odds['double_away'], f'Double Chance X2 (Draw or {away})')
                
                dnb: dict = goals.get('dnb') or {}
                if dnb.get('home', 0) >= 80:
                    save_tip(match, 'DNB_HOME', dnb['home'], f'Draw No Bet - {home}')
                elif dnb.get('away', 0) >= 80:
                    save_tip(match, 'DNB_AWAY', dnb['away'], f'Draw No Bet - {away}')
                
                # ========== CLEAN SHEET / WIN TO NIL ==========
                home_special: dict = goals.get('home_special') or {}
                away_special: dict = goals.get('away_special') or {}
                
                if home_special.get('clean_sheet', 0) >= 65:
                    save_tip(match, 'HOME_CS', home_special['clean_sheet'], f'{home} Clean Sheet')
                if away_special.get('clean_sheet', 0) >= 65:
                    save_tip(match, 'AWAY_CS', away_special['clean_sheet'], f'{away} Clean Sheet')
                if home_special.get('win_to_nil', 0) >= 65:
                    save_tip(match, 'HOME_WTN', home_special['win_to_nil'], f'{home} Win to Nil')
                if away_special.get('win_to_nil', 0) >= 65:
                    save_tip(match, 'AWAY_WTN', away_special['win_to_nil'], f'{away} Win to Nil')
                
                # ========== HANDICAPS ==========
                handicaps: dict = goals.get('handicaps') or {}
                if handicaps.get('home_minus_0_5', 0) >= 70:
                    save_tip(match, 'HC_HOME_M05', handicaps['home_minus_0_5'], f'{home} -0.5 (AH)')
                
                # ========== CORNERS ==========
                if corners and corners.get('match_has_data'):
                    m_overs: dict = corners.get('match_overs') or {}
                    if m_overs.get(6, 0) >= 80: save_tip(match, 'CORNERS_OVER_65', m_overs[6], 'Over 6.5 Corners')
                    if m_overs.get(7, 0) >= 80: save_tip(match, 'CORNERS_OVER_75', m_overs[7], 'Over 7.5 Corners')
                    if m_overs.get(8, 0) >= 80: save_tip(match, 'CORNERS_OVER_85', m_overs[8], 'Over 8.5 Corners')
                    
                    wc: dict = corners.get('winner_corners') or {}
                    if wc.get('home', 0) >= 70: save_tip(match, 'CORNER_WIN_H', wc['home'], f'{home} Wins Corners')
                    elif wc.get('away', 0) >= 70: save_tip(match, 'CORNER_WIN_A', wc['away'], f'{away} Wins Corners')

            except Exception as e:
                continue

        self.stdout.write(self.style.SUCCESS(f"Scanner finalizado! Criados: {created_count}, Atualizados: {updated_count}, Pulados (Futuros): {skipped_count}"))

        try:
            from django.core.cache import cache
            from django.core.cache.utils import make_template_fragment_key
            for lang in ['pt-br', 'en']:
                for fragment in ['premium_dashboard_html_v8', 'premium_tickets_pane']:
                    key = make_template_fragment_key(fragment, [lang])
                    cache.delete(key)
            self.stdout.write(self.style.SUCCESS("Cache do dashboard premium invalidado com sucesso!"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Aviso ao limpar cache: {e}"))
