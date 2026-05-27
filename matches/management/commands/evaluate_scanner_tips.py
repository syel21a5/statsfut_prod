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
                    
                elif tip.market == 'OVER_15':
                    is_green = total_goals >= 2
                    
                elif tip.market == 'OVER_25':
                    is_green = total_goals >= 3
                    
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
