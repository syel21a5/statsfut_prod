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
        end_date = start_of_day + timedelta(days=8)
        
        matches = Match.objects.filter(
            date__range=(start_of_day, end_date),
            status__in=['NS', 'Not Started', 'Scheduled', 'TBD', 'POSTPONED', 'Postponed']
        ).select_related('home_team', 'away_team', 'league')

        if not matches.exists():
            self.stdout.write("Nenhum jogo encontrado para gerar bilhetes.")
            return

        # Dicionário para coletar opções agrupadas por data local (America/Sao_Paulo)
        # { date_obj: { 'ht_goal': [], 'over_15': [], ... } }
        by_date_pools = {}
        skipped_count = 0

        for m in matches:
            # Otimização: Pular jogos futuros (>= 2 dias) que já possuem bilhetes gerados
            m_date = m.date.astimezone(br_tz).date()
            diff_days = (m_date - now_br.date()).days
            if diff_days >= 2:
                if BetTicketSelection.objects.filter(match=m).exists():
                    skipped_count += 1
                    continue

            if m_date not in by_date_pools:
                by_date_pools[m_date] = {
                    'ht_goal': [],
                    'over_15': [],
                    'btts': [],
                    'corners': [],
                    'favorites': [],
                    'over_05': [],
                    'under_35': [],
                    'btts_no': [],
                    'double_chance': [],
                    'hedge_favorito': [],
                    'trixie_dc_goals': [],
                    'trixie_goals_btts': [],
                    'trixie_half_goals': [],
                    'trixie_team_half': []
                }
            
            pool = by_date_pools[m_date]

            try:
                analyzer = MatchAnalyzer(m)
                goals = analyzer.get_goal_markets()
                corners = analyzer.get_corner_markets()
                odds = analyzer.get_match_odds_probs()
                
                # 1. Gol no 1º Tempo (HT Goal)
                ht_goal = goals.get('ht_goal', 0)
                if ht_goal >= 75:
                    pool['ht_goal'].append({'match': m, 'market': 'ht_goal', 'label': 'Gol no 1º Tempo', 'prob': ht_goal})
                
                # 2. Over 1.5 Gols FT
                over_15 = goals.get('over_15', 0)
                if over_15 >= 80:
                    pool['over_15'].append({'match': m, 'market': 'over_15', 'label': 'Mais de 1.5 Gols FT', 'prob': over_15})
                
                # 3. Ambas Marcam (BTTS)
                btts = goals.get('btts', 0)
                if btts >= 65:
                    pool['btts'].append({'match': m, 'market': 'btts', 'label': 'Ambas Marcam - Sim', 'prob': btts})
                
                # 4. Escanteios (Over 9.5)
                over9_corners = corners.get('match_overs', {}).get(9, 0)
                if over9_corners >= 70:
                    pool['corners'].append({'match': m, 'market': 'over_95_corners', 'label': 'Mais de 9.5 Escanteios', 'prob': over9_corners})
                
                # 5. Favorito Seguro (Back Favorito)
                home_win = odds.get('home_win', 0)
                away_win = odds.get('away_win', 0)
                if home_win >= 70:
                    pool['favorites'].append({'match': m, 'market': 'home_win', 'label': f'Vitória do {m.home_team.name}', 'prob': home_win})
                elif away_win >= 70:
                    pool['favorites'].append({'match': m, 'market': 'away_win', 'label': f'Vitória do {m.away_team.name}', 'prob': away_win})

                # 6. Over 0.5 Gols FT (Alavancagem)
                over_05 = goals.get('over_05', 0)
                if over_05 >= 90:
                    pool['over_05'].append({'match': m, 'market': 'over_05', 'label': 'Mais de 0.5 Gols FT', 'prob': over_05})

                # 7. Menos de 3.5 Gols FT (Under 3.5 Gols)
                over_35 = goals.get('over_35', 0)
                under_35 = 100 - over_35
                if under_35 >= 80:
                    pool['under_35'].append({'match': m, 'market': 'under_35', 'label': 'Menos de 3.5 Gols FT', 'prob': under_35})

                # 8. Ambas Marcam Não (BTTS No)
                btts_no = 100 - btts
                if btts_no >= 65:
                    pool['btts_no'].append({'match': m, 'market': 'btts_no', 'label': 'Ambas Marcam - Não', 'prob': btts_no})

                # 9. Dupla Chance (1X ou X2 Segura)
                double_home = odds.get('double_home', 0)
                double_away = odds.get('double_away', 0)
                if double_home >= 80:
                    pool['double_chance'].append({'match': m, 'market': 'double_chance_1x', 'label': f'1X - {m.home_team.name} ou Empate', 'prob': double_home})
                elif double_away >= 80:
                    pool['double_chance'].append({'match': m, 'market': 'double_chance_x2', 'label': f'X2 - {m.away_team.name} ou Empate', 'prob': double_away})

                # 10. Hedge ao Favorito
                if m.home_team_win_odds and m.away_team_win_odds:
                    if m.home_team_win_odds < m.away_team_win_odds and m.home_team_win_odds >= 2.00:
                        if goals.get('over_15', 0) >= 70:
                            pool['hedge_favorito'].append({'match': m, 'market': 'home_win', 'label': f'Hedge - Vitória do {m.home_team.name}', 'prob': int(100/m.home_team_win_odds)})
                    elif m.away_team_win_odds < m.home_team_win_odds and m.away_team_win_odds >= 2.00:
                        if goals.get('over_15', 0) >= 70:
                            pool['hedge_favorito'].append({'match': m, 'market': 'away_win', 'label': f'Hedge - Vitória do {m.away_team.name}', 'prob': int(100/m.away_team_win_odds)})

                # 11. Trixie Combo Bets (New Strategies)
                dc_brackets = goals.get('dc_brackets', {})
                goals_btts = goals.get('goals_btts', {})
                half_most = goals.get('half_most_goals', {})
                team_scoring = goals.get('team_scoring_halves', {})

                # Grupo 1: DC + 2-4 Gols
                if dc_brackets.get('1X_2_4', 0) >= 40:
                    pool['trixie_dc_goals'].append({'match': m, 'market': 'dc_1x_2_4', 'label': f'{m.home_team.name} ou Empate & 2-4 Gols no Jogo', 'prob': dc_brackets['1X_2_4'], 'odd': 1.85})
                elif dc_brackets.get('X2_2_4', 0) >= 40:
                    pool['trixie_dc_goals'].append({'match': m, 'market': 'dc_x2_2_4', 'label': f'Empate ou {m.away_team.name} & 2-4 Gols no Jogo', 'prob': dc_brackets['X2_2_4'], 'odd': 1.85})

                # Grupo 2: Gols + BTTS
                if goals_btts.get('over_25_yes', 0) >= 55:
                    pool['trixie_goals_btts'].append({'match': m, 'market': 'over_25_yes', 'label': '+2.5 Gols & Ambas Sim', 'prob': goals_btts['over_25_yes'], 'odd': 2.30})
                elif goals_btts.get('under_25_no', 0) >= 55:
                    pool['trixie_goals_btts'].append({'match': m, 'market': 'under_25_no', 'label': '-2.5 Gols & Ambas Não', 'prob': goals_btts['under_25_no'], 'odd': 2.20})

                # Grupo 3: 2º Tempo com Mais Gols
                if half_most.get('2t', 0) >= 65:
                    pool['trixie_half_goals'].append({'match': m, 'market': 'most_goals_2t', 'label': '2º Tempo Com Mais Gols', 'prob': half_most['2t'], 'odd': 2.05})

                # Grupo 4: Equipe Marca no 2º Tempo
                if team_scoring.get('home_2t', 0) >= 70:
                    pool['trixie_team_half'].append({'match': m, 'market': 'home_score_2t', 'label': f'{m.home_team.name} Marca no 2º Tempo', 'prob': team_scoring['home_2t'], 'odd': 1.70})
                elif team_scoring.get('away_2t', 0) >= 70:
                    pool['trixie_team_half'].append({'match': m, 'market': 'away_score_2t', 'label': f'{m.away_team.name} Marca no 2º Tempo', 'prob': team_scoring['away_2t'], 'odd': 1.70})

            except Exception:
                continue

        # Limpar bilhetes pendentes anteriores para evitar duplicar
        BetTicket.objects.filter(status='Pending', date_target__gte=start_of_day.date()).delete()

        created_count = 0

        # Iterar sobre cada data e gerar os bilhetes de forma isolada
        for target_date, pool in by_date_pools.items():
            # Ordenar tudo pelas maiores probabilidades
            pool['ht_goal'].sort(key=lambda x: x['prob'], reverse=True)
            pool['over_15'].sort(key=lambda x: x['prob'], reverse=True)
            pool['btts'].sort(key=lambda x: x['prob'], reverse=True)
            pool['corners'].sort(key=lambda x: x['prob'], reverse=True)
            pool['favorites'].sort(key=lambda x: x['prob'], reverse=True)
            pool['over_05'].sort(key=lambda x: x['prob'], reverse=True)
            pool['under_35'].sort(key=lambda x: x['prob'], reverse=True)
            pool['btts_no'].sort(key=lambda x: x['prob'], reverse=True)
            pool['double_chance'].sort(key=lambda x: x['prob'], reverse=True)
            pool['hedge_favorito'].sort(key=lambda x: x['prob'], reverse=True)

            # ==========================================
            # 1. GERAR ATÉ 6-8 DUPLAS (Doubles)
            # ==========================================
            doubles_created = 0
            
            doubles_pool_sources = [
                {'opts': pool['ht_goal'], 'title': 'Dupla Ouro HT (Gols no 1º Tempo)'},
                {'opts': pool['over_15'], 'title': 'Dupla de Gols FT (Mais de 1.5 Gols)'},
                {'opts': pool['corners'], 'title': 'Dupla de Cantos (Over 9.5 Escanteios)'},
                {'opts': pool['btts'], 'title': 'Dupla Ambas Marcam (Gols dos Dois Lados)'},
                {'opts': pool['favorites'], 'title': 'Dupla de Favoritos (Vitórias Claras)'},
                {'opts': pool['under_35'], 'title': 'Dupla Sob Controle (Menos de 3.5 Gols)'},
                {'opts': pool['btts_no'], 'title': 'Dupla Defesa de Ferro (Ambas Marcam Não)'},
                {'opts': pool['double_chance'], 'title': 'Dupla Dupla Chance (Segurança Extra)'},
            ]
            
            for source in doubles_pool_sources:
                if doubles_created >= 8:
                    break
                    
                opts = source['opts']
                title = source['title']
                
                i = 0
                group_idx = 65 # Char 'A'
                while i + 1 < len(opts) and doubles_created < 8:
                    chunk = opts[i:i+2]
                    avg_prob = sum(x['prob'] for x in chunk) // 2
                    
                    ticket_title = f"{title} - Grupo {chr(group_idx)}" if len(opts) > 2 else title
                    ticket = BetTicket.objects.create(
                        title=ticket_title,
                        ticket_type="Double",
                        average_probability=avg_prob,
                        date_target=target_date
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
                {'opts': pool['over_15'], 'title': 'Tripla de Gols FT (Mais de 1.5 Gols)'},
                {'opts': pool['double_chance'], 'title': 'Tripla Dupla Chance (Segurança Máxima)'},
                {'opts': pool['over_05'], 'title': 'Tripla Alavancagem (Mais de 0.5 Gols FT)'},
                {'opts': pool['ht_goal'], 'title': 'Tripla Ouro HT (Gols no 1º Tempo)'},
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
                        date_target=target_date
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
            for x in (pool['favorites'] + pool['over_15'] + pool['double_chance']):
                if x['prob'] >= 85:
                    multi_pool.append(x)
                    
            seen_matches = set()
            unique_multi_pool = []
            for x in sorted(multi_pool, key=lambda val: val['prob'], reverse=True):
                if x['match'].id not in seen_matches:
                    seen_matches.add(x['match'].id)
                    unique_multi_pool.append(x)
                    
            i = 0
            group_idx = 65 # 'A'
            while i + 3 < len(unique_multi_pool) and multiples_created < 2:
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
                    date_target=target_date
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
            for x in (pool['over_05'] + pool['under_35'] + pool['double_chance']):
                if x['prob'] >= 90:
                    super_pool.append(x)
                    
            seen_matches_super = set()
            unique_super_pool = []
            for x in sorted(super_pool, key=lambda val: val['prob'], reverse=True):
                if x['match'].id not in seen_matches_super:
                    seen_matches_super.add(x['match'].id)
                    unique_super_pool.append(x)
                    
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
                    date_target=target_date
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
            for sel in pool['hedge_favorito']:
                if hedge_created >= 4:
                    break
                
                ticket_title = f"Hedge ao Favorito - {sel['match'].home_team.name} x {sel['match'].away_team.name}"
                ticket = BetTicket.objects.create(
                    title=ticket_title,
                    ticket_type="Hedge_Favorito",
                    average_probability=sel['prob'],
                    date_target=target_date
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

            # ==========================================
            # 6. GERAR SISTEMAS TRIXIE (Trixie) - 4 Estratégias
            # ==========================================
            strategies = [
                {'list': pool['trixie_dc_goals'], 'name': 'DC_GOALS', 'title': 'Trixie Combo: DC + Faixa de Gols'},
                {'list': pool['trixie_goals_btts'], 'name': 'GOALS_BTTS', 'title': 'Trixie Combo: Gols + Ambas Marcam'},
                {'list': pool['trixie_half_goals'], 'name': 'HALF_GOALS', 'title': 'Trixie Especial: 2º Tempo com Mais Gols'},
                {'list': pool['trixie_team_half'], 'name': 'TEAM_HALF', 'title': 'Trixie Pressão: Equipe Marca no 2º Tempo'},
            ]

            trixie_created = 0
            for strat in strategies:
                strat_list = strat['list']
                strat_name = strat['name']
                base_title = strat['title']
                
                seen_trixie_matches = set()
                unique_trixie_pool = []
                for x in sorted(strat_list, key=lambda val: val['prob'], reverse=True):
                    if x['match'].id not in seen_trixie_matches:
                        seen_trixie_matches.add(x['match'].id)
                        unique_trixie_pool.append(x)
                
                i = 0
                group_idx = 65  # 'A'
                strat_created = 0
                while i + 2 < len(unique_trixie_pool) and strat_created < 4:  # Max 4 trixies per strategy
                    chunk = unique_trixie_pool[i:i+3]
                    avg_prob = sum(x['prob'] for x in chunk) // 3
                    
                    ticket_title = f"{base_title} - Grupo {chr(group_idx)}"
                    ticket = BetTicket.objects.create(
                        title=ticket_title,
                        ticket_type="Trixie",
                        strategy=strat_name,
                        average_probability=avg_prob,
                        date_target=target_date
                    )
                    
                    for sel in chunk:
                        BetTicketSelection.objects.create(
                            ticket=ticket,
                            match=sel['match'],
                            prediction_market=sel['market'],
                            prediction_label=sel['label'],
                            probability=sel['prob'],
                            odds_val=sel['odd']
                        )
                        
                    strat_created += 1
                    trixie_created += 1
                    created_count += 1
                    group_idx += 1
                    i += 3

        self.stdout.write(self.style.SUCCESS(f"Sucesso! Foram gerados {created_count} bilhetes com super estratégias diversas agrupados por datas isoladas."))

        # Limpa o cache automaticamente para a página Premium atualizar
        try:
            from django.core.management import call_command
            call_command('clear_cache')
            self.stdout.write(self.style.SUCCESS("Cache limpo automaticamente para atualizar a página Premium com os novos bilhetes!"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Aviso ao limpar cache: {e}"))
