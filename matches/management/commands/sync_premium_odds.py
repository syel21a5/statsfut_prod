import os
import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db.models import Q

from matches.models import Match
from matches.api_manager import APIManager

class Command(BaseCommand):
    help = 'Busca odds APENAS para os jogos Premium (com tips ativas)'

    # Limite: jogos a partir de 12h no futuro só buscam odds se ainda não tiverem
    HORAS_LIMITE_ATUALIZACAO = 12

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando Sincronizacao de Odds Premium..."))
        
        api = APIManager()
        
        # 1. Filtra jogos Premium (ScannerTip ou BetTicketSelection)
        # Janela: ultimas 6 horas ate proximas 48 horas
        time_min = now() - timedelta(hours=6)
        time_max = now() + timedelta(hours=48)
        
        premium_matches = Match.objects.filter(
            Q(scanner_tips__isnull=False) | Q(ticket_selections__isnull=False),
            date__gte=time_min,
            date__lte=time_max
        ).exclude(
            status__in=['FT', 'AET', 'PEN', 'FINISHED', 'PST', 'CANC', 'ABD']
        ).distinct()

        if not premium_matches.exists():
            self.stdout.write(self.style.WARNING("SMART SLEEP: Nenhum jogo Premium pendente de Odds no horizonte. (0 Creditos Gastos)"))
            return
        
        # 2. Separar jogos em HOJE (atualiza sempre) vs FUTURO (so busca se nao tem odds)
        limite_hoje = now() + timedelta(hours=self.HORAS_LIMITE_ATUALIZACAO)
        
        jogos_hoje = []
        jogos_futuro_sem_odds = []
        jogos_futuro_ja_tem_odds = 0
        
        for match in premium_matches:
            if not match.api_id:
                continue
            
            if match.date <= limite_hoje:
                # Jogo e HOJE ou nas proximas 12h -> sempre atualiza
                jogos_hoje.append(match)
            else:
                # Jogo e AMANHA ou depois -> so busca se NAO tem odds salvas
                if match.home_team_win_odds is None:
                    jogos_futuro_sem_odds.append(match)
                else:
                    jogos_futuro_ja_tem_odds += 1
        
        jogos_para_buscar = jogos_hoje + jogos_futuro_sem_odds
        total_candidatos = premium_matches.count()
        
        self.stdout.write(f"Total Premium: {total_candidatos} jogos")
        self.stdout.write(f"  HOJE (atualiza sempre): {len(jogos_hoje)} jogos")
        self.stdout.write(f"  FUTURO sem odds (1a busca): {len(jogos_futuro_sem_odds)} jogos")
        self.stdout.write(f"  FUTURO ja tem odds (PULANDO): {jogos_futuro_ja_tem_odds} jogos (economia de creditos)")
        
        if not jogos_para_buscar:
            self.stdout.write(self.style.WARNING("Todos os jogos futuros ja possuem odds. Nada a buscar. (0 Creditos Gastos)"))
            return
        
        self.stdout.write(f"Buscando odds para {len(jogos_para_buscar)} jogos na API...")
        
        updates = 0
        creditos_gastos = 0
        for match in jogos_para_buscar:
            self.stdout.write(f"  [Odds] Buscando para: {match.home_team.name} x {match.away_team.name}")
            
            # Tenta Bet365 primeiro (ID 8)
            odds_data = api.get_odds(match.api_id, bookmaker=8)
            creditos_gastos += 1
            time.sleep(0.5) # Protecao de rate limit
            
            chosen_bk_name = None
            markets = []
            
            if odds_data and len(odds_data) > 0:
                bookmakers = odds_data[0].get('bookmakers', [])
                if bookmakers:
                    chosen_bk_name = bookmakers[0].get('name', 'Bet365')
                    markets = bookmakers[0].get('bets', [])
                    
            if not markets:
                # Fallback generico se Bet365 falhar
                odds_data_all = api.get_odds(match.api_id, bookmaker=None)
                creditos_gastos += 1
                time.sleep(0.5)
                if odds_data_all and len(odds_data_all) > 0:
                    all_bks = odds_data_all[0].get('bookmakers', [])
                    chosen_bk = None
                    for pref_id in [8, 32, 11]: # Bet365, Betano, 1xBet
                        for bk in all_bks:
                            if bk.get('id') == pref_id:
                                chosen_bk = bk
                                break
                        if chosen_bk: break
                        
                    if not chosen_bk and all_bks:
                        chosen_bk = max(all_bks, key=lambda b: len(b.get('bets', [])))
                        
                    if chosen_bk:
                        chosen_bk_name = chosen_bk.get('name', '?')
                        markets = chosen_bk.get('bets', [])
            
            if markets:
                self.stdout.write(f"    OK Odds obtidas na {chosen_bk_name} ({len(markets)} mercados)")
                odds_count = 0
                
                for m in markets:
                    m_id = m.get('id')
                    vals = m.get('values', [])
                    
                    def get_odd(value_name):
                        for v in vals:
                            if str(v.get('value')) == value_name: return float(v['odd'])
                        return None
                        
                    if m_id == 1:
                        match.home_team_win_odds = get_odd('Home')
                        match.draw_odds = get_odd('Draw')
                        match.away_team_win_odds = get_odd('Away')
                        odds_count += 3
                    elif m_id == 5:
                        match.over_15_odds = get_odd('Over 1.5')
                        match.over_25_odds = get_odd('Over 2.5')
                        match.over_35_odds = get_odd('Over 3.5')
                        match.under_25_odds = get_odd('Under 2.5')
                        match.under_35_odds = get_odd('Under 3.5')
                        odds_count += 5
                    elif m_id == 6:
                        match.ht_goal_odds = get_odd('Over 0.5')
                        odds_count += 1
                    elif m_id == 72 and not match.ht_goal_odds:
                        match.ht_goal_odds = get_odd('Over 0.5')
                        if match.ht_goal_odds: odds_count += 1
                    elif m_id == 8:
                        match.btts_yes_odds = get_odd('Yes')
                        match.btts_no_odds = get_odd('No')
                        odds_count += 2
                    elif m_id == 12:
                        match.dc_1x_odds = get_odd('Home/Draw')
                        match.dc_x2_odds = get_odd('Draw/Away')
                        odds_count += 2
                        
                match.save()
                updates += 1
            else:
                self.stdout.write(f"    X Bookmakers ainda nao liberaram odds")
                
        self.stdout.write(self.style.SUCCESS(f"Concluido: {updates} jogos atualizados, ~{creditos_gastos} creditos gastos, {jogos_futuro_ja_tem_odds} jogos futuros pulados (economia)"))
