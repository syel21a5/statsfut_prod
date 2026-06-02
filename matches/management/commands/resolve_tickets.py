from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import BetTicket, BetTicketSelection, Goal

class Command(BaseCommand):
    help = 'Resolve os bilhetes pendentes verificando se deram Green ou Red'

    def handle(self, *args, **kwargs):
        self.stdout.write("Processando bilhetes pendentes...")
        pending_tickets = BetTicket.objects.filter(status='Pending')

        if not pending_tickets.exists():
            self.stdout.write("Nenhum bilhete pendente para resolver.")
            return

        for ticket in pending_tickets:
            self.stdout.write(f"Verificando bilhete: {ticket.title}")
            selections = ticket.selections.all()
            all_resolved = True
            any_red = False
            any_pending = False

            for sel in selections:
                match = sel.match
                
                # Consideramos resolvido se o jogo estiver como "Finished", "FT", ou se o placar final estiver preenchido
                is_finished = match.status in ['FT', 'Finished', 'Concluded'] or (match.home_score is not None and match.away_score is not None)
                
                if not is_finished:
                    any_pending = True
                    all_resolved = False
                    continue
                
                # Se o jogo terminou, avaliamos o mercado
                home_score = match.home_score or 0
                away_score = match.away_score or 0
                total_goals = home_score + away_score
                
                ht_home = match.ht_home_score or 0
                ht_away = match.ht_away_score or 0
                ht_goals = ht_home + ht_away

                result = 'Pending'

                if sel.prediction_market == 'over_15':
                    result = 'Green' if total_goals >= 2 else 'Red'
                elif sel.prediction_market == 'ht_goal':
                    result = 'Green' if ht_goals >= 1 else 'Red'
                elif sel.prediction_market == 'over_25':
                    result = 'Green' if total_goals >= 3 else 'Red'
                elif sel.prediction_market == 'over_05':
                    result = 'Green' if total_goals >= 1 else 'Red'
                elif sel.prediction_market == 'under_35':
                    result = 'Green' if total_goals <= 3 else 'Red'
                elif sel.prediction_market == 'btts':
                    result = 'Green' if (home_score > 0 and away_score > 0) else 'Red'
                elif sel.prediction_market == 'btts_no':
                    result = 'Green' if not (home_score > 0 and away_score > 0) else 'Red'
                elif sel.prediction_market == 'home_win':
                    result = 'Green' if home_score > away_score else 'Red'
                elif sel.prediction_market == 'away_win':
                    result = 'Green' if away_score > home_score else 'Red'
                elif sel.prediction_market == 'double_chance_1x':
                    result = 'Green' if home_score >= away_score else 'Red'
                elif sel.prediction_market == 'double_chance_x2':
                    result = 'Green' if away_score >= home_score else 'Red'
                elif sel.prediction_market == 'over_95_corners':
                    if match.home_corners is not None and match.away_corners is not None:
                        result = 'Green' if (match.home_corners + match.away_corners) >= 10 else 'Red'
                    else:
                        result = 'Void'
                elif sel.prediction_market == 'home_first':
                    # Verifica quem marcou o primeiro gol
                    first_goal = Goal.objects.filter(match=match).order_by('minute').first()
                    if first_goal:
                        result = 'Green' if first_goal.team == match.home_team else 'Red'
                    else:
                        result = 'Green' if home_score > 0 and away_score == 0 else 'Red'
                elif sel.prediction_market == 'away_first':
                    first_goal = Goal.objects.filter(match=match).order_by('minute').first()
                    if first_goal:
                        result = 'Green' if first_goal.team == match.away_team else 'Red'
                    else:
                        result = 'Green' if away_score > 0 and home_score == 0 else 'Red'
                elif sel.prediction_market == 'dc_1x_2_4':
                    result = 'Green' if (home_score >= away_score) and (2 <= total_goals <= 4) else 'Red'
                elif sel.prediction_market == 'dc_x2_2_4':
                    result = 'Green' if (away_score >= home_score) and (2 <= total_goals <= 4) else 'Red'
                elif sel.prediction_market == 'over_25_yes':
                    result = 'Green' if (total_goals >= 3) and (home_score > 0 and away_score > 0) else 'Red'
                elif sel.prediction_market == 'under_25_no':
                    result = 'Green' if (total_goals <= 2) and (not (home_score > 0 and away_score > 0)) else 'Red'
                elif sel.prediction_market == 'most_goals_2t':
                    goals_1t = ht_goals
                    goals_2t = total_goals - ht_goals
                    result = 'Green' if goals_2t > goals_1t else 'Red'
                elif sel.prediction_market == 'home_score_2t':
                    home_2t = home_score - ht_home
                    result = 'Green' if home_2t > 0 else 'Red'
                elif sel.prediction_market == 'away_score_2t':
                    away_2t = away_score - ht_away
                    result = 'Green' if away_2t > 0 else 'Red'
                else:
                    # Fallback padrão
                    result = 'Void'

                sel.status = result
                sel.save()
                
                if result == 'Red':
                    any_red = True
                
                self.stdout.write(f"  -> {match.home_team.name} x {match.away_team.name} ({sel.prediction_label}): {result}")

            # Atualizar o status geral do bilhete
            if any_red:
                ticket.status = 'Red'
                ticket.save()
                self.stdout.write(self.style.ERROR(f"Bilhete '{ticket.title}' finalizado como RED ❌"))
            elif not any_pending and all_resolved:
                # Todos deram Green
                ticket.status = 'Green'
                ticket.save()
                self.stdout.write(self.style.SUCCESS(f"Bilhete '{ticket.title}' finalizado como GREEN ✅"))
            else:
                self.stdout.write(f"Bilhete '{ticket.title}' continua Pendente (aguardando mais jogos).")

        self.stdout.write(self.style.SUCCESS("Processamento de bilhetes concluído!"))
