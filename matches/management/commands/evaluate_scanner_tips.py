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
                    
                elif tip.market == 'HT_GOALS_NOT_2_4':
                    if m.ht_home_score is not None and m.ht_away_score is not None:
                        ht_g = m.ht_home_score + m.ht_away_score
                        is_green = not (2 <= ht_g <= 4)
                    else:
                        goals_ht_count = m.goals.filter(minute__lte=45).count()
                        is_green = not (2 <= goals_ht_count <= 4)
                        
                elif tip.market == 'SH_GOALS_NOT_2_4':
                    if m.ht_home_score is not None and m.ht_away_score is not None and m.home_score is not None and m.away_score is not None:
                        sh_g = (m.home_score + m.away_score) - (m.ht_home_score + m.ht_away_score)
                        is_green = not (2 <= sh_g <= 4)
                    else:
                        goals_sh_count = m.goals.filter(minute__gt=45).count()
                        is_green = not (2 <= goals_sh_count <= 4)
                        
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

                elif tip.market.startswith('DC_1X_BTTS_'):
                    suffix = tip.market.split('_')[-1]
                    has_dc = m.home_score >= m.away_score
                    btts_match = (m.home_score > 0 and m.away_score > 0)
                    is_green = has_dc and (btts_match if suffix == 'YES' else not btts_match)

                elif tip.market.startswith('DC_X2_BTTS_'):
                    suffix = tip.market.split('_')[-1]
                    has_dc = m.away_score >= m.home_score
                    btts_match = (m.home_score > 0 and m.away_score > 0)
                    is_green = has_dc and (btts_match if suffix == 'YES' else not btts_match)
                    
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
                    
                elif tip.market == 'UNDER_65':
                    is_green = total_goals <= 6
                    
                elif tip.market == 'BTTS':
                    is_green = (m.home_score > 0 and m.away_score > 0)
                    
                elif tip.market == 'HOME_WIN':
                    is_green = m.home_score > m.away_score
                    
                elif tip.market == 'AWAY_WIN':
                    is_green = m.away_score > m.home_score
                    
                elif tip.market == 'FIRST_SCORE_HOME':
                    # Checar eventos de gol (quem marcou o primeiro)
                    first_goal = m.goals.order_by('minute').first()
                    if first_goal:
                        is_green = first_goal.team_id == m.home_team_id
                    else:
                        is_green = False # 0x0 deu red
                        
                elif tip.market == 'FIRST_SCORE_AWAY':
                    first_goal = m.goals.order_by('minute').first()
                    if first_goal:
                        is_green = first_goal.team_id == m.away_team_id
                    else:
                        is_green = False
                        
                elif tip.market == 'CORNERS_OVER_95':
                    # Se tiver dados de cantos salvos no Match
                    if m.home_corners is not None and m.away_corners is not None:
                        total_corners = m.home_corners + m.away_corners
                        is_green = total_corners >= 10
                    else:
                        # Se não tem dados de cantos, não dá pra avaliar agora
                        continue

                tip.status = 'GREEN' if is_green else 'RED'
                tip.save(update_fields=['status', 'updated_at'])
                
                if is_green: green_count += 1
                else: red_count += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Erro ao avaliar dica ID {tip.id}: {e}"))
                continue

        self.stdout.write(self.style.SUCCESS(f"Avaliação finalizada! Greens: {green_count}, Reds: {red_count}"))
