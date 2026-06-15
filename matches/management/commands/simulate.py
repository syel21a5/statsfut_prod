from django.core.management.base import BaseCommand
from datetime import timedelta
from django.utils import timezone
from matches.models import Match
from matches.services.advanced_stats import MatchAnalyzer

class Command(BaseCommand):
    help = 'Simulate tips over past matches'

    def handle(self, *args, **options):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=15) # last 15 days
        
        matches = Match.objects.filter(
            status__in=['FT', 'Finished', 'Match Finished']
        ).select_related('home_team', 'away_team').order_by('-date')[:1000]

        self.stdout.write(f"Simulando em uma base de {matches.count()} jogos passados...")

        stats = {
            'HOME_WIN_70': {'hits': 0, 'total': 0},
            'HOME_WIN_75': {'hits': 0, 'total': 0},
            'HOME_WIN_80': {'hits': 0, 'total': 0},
            'DC_1X_80': {'hits': 0, 'total': 0},
            'DC_1X_85': {'hits': 0, 'total': 0},
            'DC_1X_90': {'hits': 0, 'total': 0},
            'DNB_HOME_75': {'hits': 0, 'total': 0},
            'DNB_HOME_80': {'hits': 0, 'total': 0},
            'CORNERS_O75_75': {'hits': 0, 'total': 0},
            'CORNERS_O75_80': {'hits': 0, 'total': 0},
            'CORNERS_O85_75': {'hits': 0, 'total': 0},
            'CORNERS_O85_80': {'hits': 0, 'total': 0},
            'CORNER_WIN_H_70': {'hits': 0, 'total': 0},
            'CORNER_WIN_H_80': {'hits': 0, 'total': 0},
        }

        for match in matches:
            try:
                if match.home_score is None or match.away_score is None: continue
                
                analyzer = MatchAnalyzer(match)
                if len(analyzer.home_last_10) < 6 or len(analyzer.away_last_10) < 6: continue
                
                goals = analyzer.get_goal_markets() or {}
                corners = analyzer.get_corner_markets() or {}
                odds = analyzer.get_match_odds_probs() or {}
                
                home_len = len(analyzer.home_last_10)
                away_len = len(analyzer.away_last_10)
                
                # Resolving match result
                total_goals = match.home_score + match.away_score
                home_win = match.home_score > match.away_score
                away_win = match.away_score > match.home_score
                draw = match.home_score == match.away_score
                dc_1x = home_win or draw
                
                # Resolving corners
                home_corners = match.home_corners if match.home_corners else 0
                away_corners = match.away_corners if match.away_corners else 0
                total_corners = home_corners + away_corners
                corner_win_h = home_corners > away_corners

                # HOME WIN
                p_home_win = odds.get('home_win', 0)
                if p_home_win >= 70:
                    stats['HOME_WIN_70']['total'] += 1
                    if home_win: stats['HOME_WIN_70']['hits'] += 1
                if p_home_win >= 75:
                    stats['HOME_WIN_75']['total'] += 1
                    if home_win: stats['HOME_WIN_75']['hits'] += 1
                if p_home_win >= 80:
                    stats['HOME_WIN_80']['total'] += 1
                    if home_win: stats['HOME_WIN_80']['hits'] += 1

                # DOUBLE CHANCE 1X
                p_dc_1x = odds.get('double_home', 0)
                if p_dc_1x >= 80:
                    stats['DC_1X_80']['total'] += 1
                    if dc_1x: stats['DC_1X_80']['hits'] += 1
                if p_dc_1x >= 85:
                    stats['DC_1X_85']['total'] += 1
                    if dc_1x: stats['DC_1X_85']['hits'] += 1
                if p_dc_1x >= 90:
                    stats['DC_1X_90']['total'] += 1
                    if dc_1x: stats['DC_1X_90']['hits'] += 1

                # DRAW NO BET HOME
                dnb = goals.get('dnb') or {}
                p_dnb_h = dnb.get('home', 0)
                if p_dnb_h >= 75:
                    stats['DNB_HOME_75']['total'] += 1
                    if home_win: stats['DNB_HOME_75']['hits'] += 1
                    elif draw: stats['DNB_HOME_75']['total'] -= 1 # Void
                if p_dnb_h >= 80:
                    stats['DNB_HOME_80']['total'] += 1
                    if home_win: stats['DNB_HOME_80']['hits'] += 1
                    elif draw: stats['DNB_HOME_80']['total'] -= 1 # Void

                # CORNERS
                if corners and corners.get('match_has_data') and total_corners > 0:
                    m_overs = corners.get('match_overs') or {}
                    p_over_75 = m_overs.get(7, 0)
                    p_over_85 = m_overs.get(8, 0)
                    
                    if p_over_75 >= 75:
                        stats['CORNERS_O75_75']['total'] += 1
                        if total_corners > 7.5: stats['CORNERS_O75_75']['hits'] += 1
                    if p_over_75 >= 80:
                        stats['CORNERS_O75_80']['total'] += 1
                        if total_corners > 7.5: stats['CORNERS_O75_80']['hits'] += 1
                        
                    if p_over_85 >= 75:
                        stats['CORNERS_O85_75']['total'] += 1
                        if total_corners > 8.5: stats['CORNERS_O85_75']['hits'] += 1
                    if p_over_85 >= 80:
                        stats['CORNERS_O85_80']['total'] += 1
                        if total_corners > 8.5: stats['CORNERS_O85_80']['hits'] += 1
                        
                    wc = corners.get('winner_corners') or {}
                    p_wc_h = wc.get('home', 0)
                    if p_wc_h >= 70:
                        stats['CORNER_WIN_H_70']['total'] += 1
                        if corner_win_h: stats['CORNER_WIN_H_70']['hits'] += 1
                    if p_wc_h >= 80:
                        stats['CORNER_WIN_H_80']['total'] += 1
                        if corner_win_h: stats['CORNER_WIN_H_80']['hits'] += 1

            except Exception as e:
                import traceback
                self.stdout.write(f"Error: {e}")
                self.stdout.write(traceback.format_exc())
                continue

        self.stdout.write("\n--- RESULTADOS DA SIMULACAO ---")
        for market, data in stats.items():
            if data['total'] > 0:
                winrate = (data['hits'] / data['total']) * 100
                self.stdout.write(f"{market}: {data['hits']}/{data['total']} greens ({winrate:.1f}%)")
            else:
                self.stdout.write(f"{market}: Nenhuma tip gerada")
