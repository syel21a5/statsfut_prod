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
        hedge_favorito_opts = [] # Hedge ao Favorito

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

                # 10. Hedge ao Favorito
                if m.home_team_win_odds and m.away_team_win_odds:
                    if m.home_team_win_odds < m.away_team_win_odds and m.home_team_win_odds >= 2.00:
                        if goals.get('over_15', 0) >= 70:
                            hedge_favorito_opts.append({'match': m, 'market': 'home_win', 'label': f'Hedge - Vitória do {m.home_team.name}', 'prob': int(100/m.home_team_win_odds)})
                    elif m.away_team_win_odds < m.home_team_win_odds and m.away_team_win_odds >= 2.00:
                        if goals.get('over_15', 0) >= 70:
                            hedge_favorito_opts.append({'match': m, 'market': 'away_win', 'label': f'Hedge - Vitória do {m.away_team.name}', 'prob': int(100/m.away_team_win_odds)})

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
        hedge_favorito_opts.sort(key=lambda x: x['prob'], reverse=True)

        # Limpar bilhetes pendentes anteriores para evitar duplicar no mesmo dia
        BetTicket.objects.filter(status='Pending', date_target=start_of_day.date()).delete()

        created_count = 0

        # ==========================================
        # 1. GERAR ATÉ 6-8 DUPLAS (Doubles)
        # ==========================================
        doubles_created = 0
        
        # Mapeamos as opções de duplas disponíveis e definimos a ordem de prioridade
        doubles_pool_sources = [
            {'opts': ht_goal_opts, 'title': 'Dupla Ouro HT (Gols no 1º Tempo)'},
            {'opts': over15_opts, 'title': 'Dupla de Gols FT (Mais de 1.5 Gols)'},
            {'opts': corners_opts, 'title': 'Dupla de Cantos (Over 9.5 Escanteios)'},
            {'opts': btts_opts, 'title': 'Dupla Ambas Marcam (Gols dos Dois Lados)'},
            {'opts': favorites_opts, 'title': 'Dupla de Favoritos (Vitórias Claras)'},
            {'opts': under35_opts, 'title': 'Dupla Sob Controle (Menos de 3.5 Gols)'},
            {'opts': btts_no_opts, 'title': 'Dupla Defesa de Ferro (Ambas Marcam Não)'},
            {'opts': double_chance_opts, 'title': 'Dupla Dupla Chance (Segurança Extra)'},
        ]
        
        # Para cada categoria, tentamos extrair o máximo de duplas (chunks de 2) até bater o limite de 8
        for source in doubles_pool_sources:
            if doubles_created >= 8:
                break
                
            opts = source['opts']
            title = source['title']
            
            # Divide os itens ordenados daquela categoria em grupos de 2
            i = 0
            group_idx = 65 # Char 'A'
            while i + 1 < len(opts) and doubles_created < 8:
                chunk = opts[i:i+2]
                avg_prob = sum(x['prob'] for x in chunk) // 2
                
                # Gera o bilhete
                ticket_title = f"{title} - Grupo {chr(group_idx)}" if len(opts) > 2 else title
                ticket = BetTicket.objects.create(
                    title=ticket_title,
                    ticket_type="Double",
                    average_probability=avg_prob,
                    date_target=start_of_day.date()
                )
                
                for sel in chunk:
                    BetTicketSelection.objects.create(
                        ticket=ticket,
                        match=sel['match'],
                        prediction_market=sel['market'],
                        prediction_label=sel['label'],
                        probability=sel['prob']
                    )
                
                doubles_created += 1
                created_count += 1
                group_idx += 1
                i += 2

        # ==========================================
        # 2. GERAR ATÉ 4 TRIPLAS (Trebles)
        # ==========================================
        triples_created = 0
        
        triples_pool_sources = [
            {'opts': over15_opts, 'title': 'Tripla de Gols FT (Mais de 1.5 Gols)'},
            {'opts': double_chance_opts, 'title': 'Tripla Dupla Chance (Segurança Máxima)'},
            {'opts': over05_opts, 'title': 'Tripla Alavancagem (Mais de 0.5 Gols FT)'},
            {'opts': ht_goal_opts, 'title': 'Tripla Ouro HT (Gols no 1º Tempo)'},
        ]
        
        for source in triples_pool_sources:
            if triples_created >= 4:
                break
                
            opts = source['opts']
            title = source['title']
            
            i = 0
            group_idx = 65 # 'A'
            while i + 2 < len(opts) and triples_created < 4:
                chunk = opts[i:i+3]
                avg_prob = sum(x['prob'] for x in chunk) // 3
                
                ticket_title = f"{title} - Grupo {chr(group_idx)}" if len(opts) > 3 else title
                ticket = BetTicket.objects.create(
                    title=ticket_title,
                    ticket_type="Treble",
                    average_probability=avg_prob,
                    date_target=start_of_day.date()
                )
                
                for sel in chunk:
                    BetTicketSelection.objects.create(
                        ticket=ticket,
                        match=sel['match'],
                        prediction_market=sel['market'],
                        prediction_label=sel['label'],
                        probability=sel['prob']
                    )
                    
                triples_created += 1
                created_count += 1
                group_idx += 1
                i += 3

        # ==========================================
        # 3. GERAR ATÉ 2 MÚLTIPLAS DE OURO (Multiple_4_5)
        # ==========================================
        multiples_created = 0
        
        multi_pool = []
        for x in (favorites_opts + over15_opts + double_chance_opts):
            if x['prob'] >= 85:
                multi_pool.append(x)
                
        # Deduplica partidas para não repetir o mesmo jogo em múltiplas
        seen_matches = set()
        unique_multi_pool = []
        for x in sorted(multi_pool, key=lambda val: val['prob'], reverse=True):
            if x['match'].id not in seen_matches:
                seen_matches.add(x['match'].id)
                unique_multi_pool.append(x)
                
        # Pega grupos de 4 a 5 jogos para montar até 2 múltiplas
        i = 0
        group_idx = 65 # 'A'
        while i + 3 < len(unique_multi_pool) and multiples_created < 2:
            # Pega de 4 a 5 no máximo (tenta pegar 5 se tiver, se não, pega 4)
            size = min(5, len(unique_multi_pool) - i)
            if size < 4:
                break
                
            chunk = unique_multi_pool[i:i+size]
            avg_prob = sum(x['prob'] for x in chunk) // len(chunk)
            
            ticket_title = f"Múltipla de Ouro (Segurança & Valor) - Grupo {chr(group_idx)}" if group_idx > 65 or len(unique_multi_pool) > 5 else "Múltipla de Ouro (Segurança & Valor)"
            ticket = BetTicket.objects.create(
                title=ticket_title,
                ticket_type="Multiple_4_5",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            
            for sel in chunk:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
                
            multiples_created += 1
            created_count += 1
            group_idx += 1
            i += size

        # ==========================================
        # 4. GERAR ATÉ 2 SUPER MÚLTIPLAS (Super_6_8)
        # ==========================================
        supers_created = 0
        
        super_pool = []
        for x in (over05_opts + under35_opts + double_chance_opts):
            if x['prob'] >= 90:
                super_pool.append(x)
                
        seen_matches_super = set()
        unique_super_pool = []
        for x in sorted(super_pool, key=lambda val: val['prob'], reverse=True):
            if x['match'].id not in seen_matches_super:
                seen_matches_super.add(x['match'].id)
                unique_super_pool.append(x)
                
        # Pega grupos de 6 a 8 jogos para montar até 2 super múltiplas
        i = 0
        group_idx = 65 # 'A'
        while i + 5 < len(unique_super_pool) and supers_created < 2:
            size = min(8, len(unique_super_pool) - i)
            if size < 6:
                break
                
            chunk = unique_super_pool[i:i+size]
            avg_prob = sum(x['prob'] for x in chunk) // len(chunk)
            
            ticket_title = f"Super Múltipla Alavancagem (Odds Gigantes) - Grupo {chr(group_idx)}" if group_idx > 65 or len(unique_super_pool) > 8 else "Super Múltipla Alavancagem (Odds Gigantes)"
            ticket = BetTicket.objects.create(
                title=ticket_title,
                ticket_type="Super_6_8",
                average_probability=avg_prob,
                date_target=start_of_day.date()
            )
            
            for sel in chunk:
                BetTicketSelection.objects.create(
                    ticket=ticket,
                    match=sel['match'],
                    prediction_market=sel['market'],
                    prediction_label=sel['label'],
                    probability=sel['prob']
                )
                
            supers_created += 1
            created_count += 1
            group_idx += 1
            i += size

        # ==========================================
        # 5. GERAR ATÉ 4 HEDGE AO FAVORITO (Hedge_Favorito)
        # ==========================================
        hedge_created = 0
        for sel in hedge_favorito_opts:
            if hedge_created >= 4:
                break
            
            ticket_title = f"Hedge ao Favorito - {sel['match'].home_team.name} x {sel['match'].away_team.name}"
            ticket = BetTicket.objects.create(
                title=ticket_title,
                ticket_type="Hedge_Favorito",
                average_probability=sel['prob'],
                date_target=start_of_day.date()
            )
            
            BetTicketSelection.objects.create(
                ticket=ticket,
                match=sel['match'],
                prediction_market=sel['market'],
                prediction_label=sel['label'],
                probability=sel['prob']
            )
            
            hedge_created += 1
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Sucesso! Foram gerados {created_count} bilhetes com super estratégias diversas hoje."))

