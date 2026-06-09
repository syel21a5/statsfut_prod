import sys
from django.core.management.base import BaseCommand
from matches.models import ScannerTip

class Command(BaseCommand):
    help = 'Avalia as dicas pendentes cruzando com o placar final do jogo para definir Green ou Red.'

    def handle(self, *args, **options):
        # Jogos finalizados que possuem dicas pendentes
        finished_statuses = ['FT', 'Finished', 'AET', 'PEN', 'Match Finished']
        
        pending_tips = ScannerTip.objects.filter(
            status='PENDING',
            match__status__in=finished_statuses
        ).select_related('match')

        self.stdout.write(f"Avaliando {pending_tips.count()} dicas pendentes...")

        green_count = 0
        red_count = 0
        
        for tip in pending_tips:
            m = tip.match
            try:
                # Se não temos placar válido, pula (pode ser que a API não tenha atualizado os gols)
                if m.home_score is None or m.away_score is None:
                    continue
                    
                total_goals = m.home_score + m.away_score
                is_green = False
                
                if tip.market == 'HT_GOAL':
                    # Como na API não temos HT score confiável guardado nativamente, 
                    # a avaliação precisa checar os Goal events. Se houver algum gol com minute <= 45.
                    goals_ht = m.goals.filter(minute__lte=45).exists()
                    is_green = goals_ht
                    
                elif tip.market == 'DNB_HOME':
                    if m.home_score == m.away_score:
                        tip.status = 'VOID'
                        tip.save(update_fields=['status', 'updated_at'])
                        continue
                    is_green = m.home_score > m.away_score
                    
                elif tip.market == 'DNB_AWAY':
                    if m.home_score == m.away_score:
                        tip.status = 'VOID'
                        tip.save(update_fields=['status', 'updated_at'])
                        continue
                    is_green = m.away_score > m.home_score
                    
                elif tip.market == 'DC_1X':
                    is_green = m.home_score >= m.away_score
                    
                elif tip.market == 'DC_X2':
                    is_green = m.away_score >= m.home_score
                    
                elif tip.market == 'HOME_CS':
                    is_green = m.away_score == 0
                    
                elif tip.market == 'AWAY_CS':
                    is_green = m.home_score == 0
                    
                elif tip.market == 'HOME_WTN':
                    is_green = m.home_score > m.away_score and m.away_score == 0
                    
                elif tip.market == 'AWAY_WTN':
                    is_green = m.away_score > m.home_score and m.home_score == 0
                    
                elif tip.market == 'HC_HOME_M05':
                    is_green = m.home_score > m.away_score
                    
                elif tip.market == 'OVER_05':
                    is_green = total_goals >= 1

                elif tip.market.startswith('DC_1X_UNDER_'):
                    line = float(tip.market.replace('DC_1X_UNDER_', '').replace('_', '.'))
                    has_dc = m.home_score >= m.away_score
                    has_under = total_goals < line
                    is_green = has_dc and has_under
                    
                elif tip.market.startswith('DC_X2_UNDER_'):
                    line = float(tip.market.replace('DC_X2_UNDER_', '').replace('_', '.'))
                    has_dc = m.away_score >= m.home_score
                    has_under = total_goals < line
                    is_green = has_dc and has_under
 
                elif tip.market.startswith('DC_1X_OVER_'):
                    line = float(tip.market.replace('DC_1X_OVER_', '').replace('_', '.'))
                    has_dc = m.home_score >= m.away_score
                    has_over = total_goals > line
                    is_green = has_dc and has_over
                    
                elif tip.market.startswith('DC_X2_OVER_'):
                    line = float(tip.market.replace('DC_X2_OVER_', '').replace('_', '.'))
                    has_dc = m.away_score >= m.home_score
                    has_over = total_goals > line
                    is_green = has_dc and has_over
                    
                elif tip.market == 'OVER_15':
                    is_green = total_goals >= 2
                    
                elif tip.market == 'OVER_25':
                    is_green = total_goals >= 3
                    
                elif tip.market == 'OVER_35':
                    is_green = total_goals >= 4
                    
                elif tip.market == 'UNDER_35':
                    is_green = total_goals <= 3
                    
                elif tip.market == 'UNDER_45':
                    is_green = total_goals <= 4
                    
                elif tip.market == 'UNDER_55':
                    is_green = total_goals <= 5
                    
                elif tip.market == 'BTTS':
                    is_green = (m.home_score > 0 and m.away_score > 0)
                    
                elif tip.market == 'HOME_WIN':
                    is_green = m.home_score > m.away_score
                    
                elif tip.market == 'AWAY_WIN':
                    is_green = m.away_score > m.home_score
                        
                elif tip.market == 'CORNERS_OVER_65':
                    if m.home_corners is not None and m.away_corners is not None:
                        is_green = (m.home_corners + m.away_corners) >= 7
                    else: continue
                elif tip.market == 'CORNERS_OVER_75':
                    if m.home_corners is not None and m.away_corners is not None:
                        is_green = (m.home_corners + m.away_corners) >= 8
                    else: continue
                elif tip.market == 'CORNERS_OVER_85':
                    if m.home_corners is not None and m.away_corners is not None:
                        is_green = (m.home_corners + m.away_corners) >= 9
                    else: continue
                elif tip.market == 'CORNER_WIN_H':
                    if m.home_corners is not None and m.away_corners is not None:
                        is_green = m.home_corners > m.away_corners
                    else: continue
                elif tip.market == 'CORNER_WIN_A':
                    if m.home_corners is not None and m.away_corners is not None:
                        is_green = m.away_corners > m.home_corners
                    else: continue

                tip.status = 'GREEN' if is_green else 'RED'
                tip.save(update_fields=['status', 'updated_at'])
                
                if is_green: green_count += 1
                else: red_count += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Erro ao avaliar dica ID {tip.id}: {e}"))
                continue

        self.stdout.write(self.style.SUCCESS(f"Avaliação finalizada! Greens: {green_count}, Reds: {red_count}"))
