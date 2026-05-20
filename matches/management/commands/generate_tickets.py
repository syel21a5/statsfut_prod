from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from zoneinfo import ZoneInfo
from matches.models import Match, BetTicket, BetTicketSelection
from matches.services.advanced_stats import MatchAnalyzer

class Command(BaseCommand):
    help = 'Gera estratégias e bilhetes especializados baseados em IA para o dia'

    def handle(self, *args, **kwargs):
        self.stdout.write("Analisando jogos com algoritmos avançados para gerar bilhetes...")
        
        br_tz = ZoneInfo('America/Sao_Paulo')
        now_br = timezone.now().astimezone(br_tz)
        start_of_day = now_br.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_of_day + timedelta(days=2)
        
        matches = Match.objects.filter(
            date__range=(start_of_day, end_date),
            status__in=['NS', 'Not Started', 'Scheduled', 'TBD', 'POSTPONED', 'Postponed']
        ).select_related('home_team', 'away_team', 'league')

        if not matches.exists():
            self.stdout.write("Nenhum jogo encontrado para gerar bilhetes.")
            return

        # Listas para coletar opções de cada estratégia
        ht_goal_opts = []      # Gol no 1º Tempo
        over15_opts = []       # Over 1.5 Gols
        btts_opts = []         # Ambas Marcam
        corners_opts = []      # Over 9.5 Cantos
        favorites_opts = []    # Vitória do Favorito
        
        # Novas Estratégias Avançadas
        over05_opts = []       # Over 0.5 Gols FT (Alavancagem/Segurança)
        under35_opts = []      # Menos de 3.5 Gols FT (Conservador)
        btts_no_opts = []      # Ambas Marcam Não (Defesa Fechada)
        double_chance_opts = [] # Dupla Chance (Segurança de Ferro)

        for m in matches:
            try:
                analyzer = MatchAnalyzer(m)
                goals = analyzer.get_goal_markets()
                corners = analyzer.get_corner_markets()
                odds = analyzer.get_match_odds_probs()
                
                # 1. Gol no 1º Tempo (HT Goal)
                ht_goal = goals.get('ht_goal', 0)
                if ht_goal >= 75:
                    ht_goal_opts.append({'match': m, 'market': 'ht_goal', 'label': 'Gol no 1º Tempo', 'prob': ht_goal})
                
                # 2. Over 1.5 Gols FT
                over_15 = goals.get('over_15', 0)
                if over_15 >= 80:
                    over15_opts.append({'match': m, 'market': 'over_15', 'label': 'Mais de 1.5 Gols FT', 'prob': over_15})
                
                # 3. Ambas Marcam (BTTS)
                btts = goals.get('btts', 0)
                if btts >= 65:
                    btts_opts.append({'match': m, 'market': 'btts', 'label': 'Ambas Marcam - Sim', 'prob': btts})
                
                # 4. Escanteios (Over 9.5)
                over9_corners = corners.get('match_overs', {}).get(9, 0)
                if over9_corners >= 70:
                    corners_opts.append({'match': m, 'market': 'over_95_corners', 'label': 'Mais de 9.5 Escanteios', 'prob': over9_corners})
                
                # 5. Favorito Seguro (Back Favorito)
                home_win = odds.get('home_win', 0)
                away_win = odds.get('away_win', 0)
                if home_win >= 70:
                    favorites_opts.append({'match': m, 'market': 'home_win', 'label': f'Vitória do {m.home_team.name}', 'prob': home_win})
                elif away_win >= 70:
                    favorites_opts.append({'match': m, 'market': 'away_win', 'label': f'Vitória do {m.away_team.name}', 'prob': away_win})

                # 6. Over 0.5 Gols FT (Alavancagem)
                over_05 = goals.get('over_05', 0)
                if over_05 >= 90:
                    over05_opts.append({'match': m, 'market': 'over_05', 'label': 'Mais de 0.5 Gols FT', 'prob': over_05})

                # 7. Menos de 3.5 Gols FT (Under 3.5 Gols)
                over_35 = goals.get('over_35', 0)
                under_35 = 100 - over_35
                if under_35 >= 80:
                    under35_opts.append({'match': m, 'market': 'under_35', 'label': 'Menos de 3.5 Gols FT', 'prob': under_35})

                # 8. Ambas Marcam Não (BTTS No)
                btts_no = 100 - btts
                if btts_no >= 65:
                    btts_no_opts.append({'match': m, 'market': 'btts_no', 'label': 'Ambas Marcam - Não', 'prob': btts_no})

                # 9. Dupla Chance (1X ou X2 Segura)
                double_home = odds.get('double_home', 0)
                double_away = odds.get('double_away', 0)
                if double_home >= 80:
                    double_chance_opts.append({'match': m, 'market': 'double_chance_1x', 'label': f'1X - {m.home_team.name} ou Empate', 'prob': double_home})
                elif double_away >= 80:
                    double_chance_opts.append({'match': m, 'market': 'double_chance_x2', 'label': f'X2 - {m.away_team.name} ou Empate', 'prob': double_away})

            except Exception as e:
                continue

        # Ordenar tudo pelas maiores probabilidades
        ht_goal_opts.sort(key=lambda x: x['prob'], reverse=True)
        over15_opts.sort(key=lambda x: x['prob'], reverse=True)
        btts_opts.sort(key=lambda x: x['prob'], reverse=True)
        corners_opts.sort(key=lambda x: x['prob'], reverse=True)
        favorites_opts.sort(key=lambda x: x['prob'], reverse=True)
        over05_opts.sort(key=lambda x: x['prob'], reverse=True)
        under35_opts.sort(key=lambda x: x['prob'], reverse=True)
        btts_no_opts.sort(key=lambda x: x['prob'], reverse=True)
        double_chance_opts.sort(key=lambda x: x['prob'], reverse=True)

        # Limpar bilhetes pendentes anteriores para evitar duplicar no mesmo dia
        BetTicket.objects.filter(status='Pending', date_target=start_of_day.date()).delete()

        created_count = 0

        # ESTRATÉGIA 1: Dupla de Gols HT (Altamente Lucrativo)
        if len(ht_goal_opts) >= 2:
            top_2 = ht_goal_opts[:2]
            avg_prob = sum(x['prob'] for x in top_2) // 2
            ticket = BetTicket.objects.create(
                title="Dupla Ouro HT (Gols no 1º Tempo)",
                ticket_type="Double",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            for sel in top_2:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
            created_count += 1

        # ESTRATÉGIA 2: Tripla Over 1.5 FT (Consistência Pura)
        if len(over15_opts) >= 3:
            top_3 = over15_opts[:3]
            avg_prob = sum(x['prob'] for x in top_3) // 3
            ticket = BetTicket.objects.create(
                title="Tripla de Gols FT (Mais de 1.5 Gols)",
                ticket_type="Treble",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            for sel in top_3:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
            created_count += 1

        # ESTRATÉGIA 3: Bilhete de Escanteios (Corners Master)
        if len(corners_opts) >= 2:
            top_2 = corners_opts[:2]
            avg_prob = sum(x['prob'] for x in top_2) // 2
            ticket = BetTicket.objects.create(
                title="Dupla de Cantos (Over 9.5 Escanteios)",
                ticket_type="Double",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            for sel in top_2:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
            created_count += 1

        # ESTRATÉGIA 4: Dupla Ambas Marcam (BTTS Especialista)
        if len(btts_opts) >= 2:
            top_2 = btts_opts[:2]
            avg_prob = sum(x['prob'] for x in top_2) // 2
            ticket = BetTicket.objects.create(
                title="Dupla Ambas Marcam (Gols dos Dois Lados)",
                ticket_type="Double",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            for sel in top_2:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
            created_count += 1

        # ESTRATÉGIA 5: Favorito de Ouro (Back Favorito Seguro)
        if len(favorites_opts) >= 2:
            top_2 = favorites_opts[:2]
            avg_prob = sum(x['prob'] for x in top_2) // 2
            ticket = BetTicket.objects.create(
                title="Favoritos Imperdíveis (Vitórias do Dia)",
                ticket_type="Double",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            for sel in top_2:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
            created_count += 1

        # ESTRATÉGIA 6: Múltipla Alavancagem (Mais de 0.5 Gols FT)
        if len(over05_opts) >= 3:
            top_3 = over05_opts[:3]
            avg_prob = sum(x['prob'] for x in top_3) // 3
            ticket = BetTicket.objects.create(
                title="Tripla Alavancagem (Mais de 0.5 Gols FT)",
                ticket_type="Treble",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            for sel in top_3:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
            created_count += 1

        # ESTRATÉGIA 7: Dupla Under Conservadora (Menos de 3.5 Gols FT)
        if len(under35_opts) >= 2:
            top_2 = under35_opts[:2]
            avg_prob = sum(x['prob'] for x in top_2) // 2
            ticket = BetTicket.objects.create(
                title="Dupla Menos de 3.5 Gols (Sob Controle)",
                ticket_type="Double",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            for sel in top_2:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
            created_count += 1

        # ESTRATÉGIA 8: Dupla Defesa de Ferro (Ambas Marcam - Não)
        if len(btts_no_opts) >= 2:
            top_2 = btts_no_opts[:2]
            avg_prob = sum(x['prob'] for x in top_2) // 2
            ticket = BetTicket.objects.create(
                title="Dupla Ambas Marcam Não (Defesa Blindada)",
                ticket_type="Double",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            for sel in top_2:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
            created_count += 1

        # ESTRATÉGIA 9: Tripla Dupla Chance Segura (1X / X2)
        if len(double_chance_opts) >= 3:
            top_3 = double_chance_opts[:3]
            avg_prob = sum(x['prob'] for x in top_3) // 3
            ticket = BetTicket.objects.create(
                title="Tripla Dupla Chance (Segurança Máxima)",
                ticket_type="Treble",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            for sel in top_3:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Sucesso! Foram gerados {created_count} bilhetes com super estratégias diversas hoje."))

