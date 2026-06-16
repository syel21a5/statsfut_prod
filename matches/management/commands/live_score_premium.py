import os
import sys
import requests
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction
from django.db.models import Q

from matches.models import Match

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Daemon Ao Vivo EXCLUSIVO para Jogos Premium (Smart Sleep & Zero Desperdício)"

    def handle(self, *args, **options):
        api_key = os.getenv("API_FOOTBALL_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY não configurada no .env!"))
            return

        headers = {
            'x-apisports-key': api_key,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }

        # 1. Filtra APENAS jogos Premium (que possuem ScannerTip ou BetTicketSelection)
        today_start = now() - timedelta(hours=24)
        today_end = now() + timedelta(hours=24)

        premium_matches = Match.objects.filter(
            Q(scanner_tips__isnull=False) | Q(ticket_selections__isnull=False),
            date__gte=today_start,
            date__lte=today_end
        ).distinct()

        # 2. Desses premium, existem jogos rodando AGORA ou começando nos próximos 15 minutos?
        active_premium = premium_matches.filter(
            status__in=['Live', 'In Play', '1H', '2H', 'HT', 'ET', 'P', 'First Half', 'Second Half', 'Halftime', 'Extra Time', 'Penalty', 'Scheduled', 'Not Started', 'Timed', 'NS']
        )
        
        is_there_active_game = False
        for m in active_premium:
            if m.status in ['Scheduled', 'Not Started', 'Timed', 'NS']:
                if m.date:
                    time_diff_hours = (now() - m.date).total_seconds() / 3600.0
                    # Acorda apenas se o jogo começa em 15 min ou começou há no máximo 1.5 horas (90 min)
                    if -0.25 <= time_diff_hours <= 1.5:
                        is_there_active_game = True
                        break
                    elif time_diff_hours > 1.5:
                        # Jogo atrasou muito e a API não entregou. Marca como adiado.
                        m.status = 'Postponed'
                        m.save()
            else:
                # É um jogo Live
                is_there_active_game = True
                break

        if not is_there_active_game:
            # Morre silenciosamente para não gastar CPU nem poluir os logs
            return

        # 3. Se chegou aqui, TEM JOGO PREMIUM ROLANDO!
        self.stdout.write(self.style.SUCCESS("🔥 JOGOS PREMIUM AO VIVO! Puxando dados globais da API (1 crédito)..."))
        
        url = "https://v3.football.api-sports.io/fixtures?live=all"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                fixtures = data.get('response', [])
                
                matches_updated = 0
                live_api_dict = {str(f['fixture']['id']): f for f in fixtures} if fixtures else {}

                with transaction.atomic():
                    for db_match in active_premium:
                        f_id = db_match.api_id
                        
                        fix_data = None
                        if f_id and str(f_id) in live_api_dict:
                            fix_data = live_api_dict[str(f_id)]

                        if not fix_data:
                            # Fallback: Tentar casar pelo nome dos times, já que o ID do banco pode ser do SofaScore (sofa_...)
                            db_home = db_match.home_team.name.lower().replace('-', ' ').strip()
                            db_away = db_match.away_team.name.lower().replace('-', ' ').strip()
                            
                            for api_f_id, api_f_data in live_api_dict.items():
                                try:
                                    api_home = api_f_data['teams']['home']['name'].lower().replace('-', ' ').strip()
                                    api_away = api_f_data['teams']['away']['name'].lower().replace('-', ' ').strip()
                                    
                                    home_match = (db_home in api_home) or (api_home in db_home)
                                    away_match = (db_away in api_away) or (api_away in db_away)
                                    
                                    if home_match and away_match:
                                        fix_data = api_f_data
                                        # Encontrou o jogo por nome! Atualizamos o ID para ser instantaneo da proxima vez
                                        db_match.api_id = str(api_f_id)
                                        break
                                except Exception:
                                    continue

                        if fix_data:
                            # Proteção Máxima: Se a API diz que está vivo, mas o jogo começou há mais de 4 horas, a API travou!
                            if db_match.date and db_match.date < now() - timedelta(hours=4):
                                db_match.status = 'FT'
                                db_match.save()
                                matches_updated += 1
                                self.stdout.write(f"  🛑 Timeout/Travado na API: {db_match.home_team.name} x {db_match.away_team.name} (Forçado FT)")
                                continue
                                
                            f_info = fix_data.get('fixture', {})
                            g_info = fix_data.get('goals', {})
                            status_info = f_info.get('status', {})
                            stats_list = fix_data.get('statistics', [])
                            
                            db_match.home_score = g_info.get('home') if g_info.get('home') is not None else db_match.home_score
                            db_match.away_score = g_info.get('away') if g_info.get('away') is not None else db_match.away_score
                            
                            elapsed_base = status_info.get('elapsed')
                            elapsed_extra = status_info.get('extra')
                            if elapsed_base is not None:
                                db_match.elapsed_time = elapsed_base + (elapsed_extra if elapsed_extra else 0)
                            
                            # Parse Statistics if available
                            if stats_list and len(stats_list) >= 2:
                                home_stats_raw = {s.get('type', ''): s.get('value') for s in stats_list[0].get('statistics', [])}
                                away_stats_raw = {s.get('type', ''): s.get('value') for s in stats_list[1].get('statistics', [])}
                                
                                def safe_int(val):
                                    try: return int(val) if val is not None else None
                                    except: return None
                                    
                                def safe_possession(val):
                                    try: return int(str(val).replace('%', '')) if val is not None else None
                                    except: return None

                                db_match.home_shots_on_target = safe_int(home_stats_raw.get('Shots on Goal'))
                                db_match.away_shots_on_target = safe_int(away_stats_raw.get('Shots on Goal'))
                                db_match.home_corners = safe_int(home_stats_raw.get('Corner Kicks'))
                                db_match.away_corners = safe_int(away_stats_raw.get('Corner Kicks'))
                                db_match.home_dangerous_attacks = safe_int(home_stats_raw.get('Dangerous Attacks')) or safe_int(home_stats_raw.get('Attacks'))
                                db_match.away_dangerous_attacks = safe_int(away_stats_raw.get('Dangerous Attacks')) or safe_int(away_stats_raw.get('Attacks'))
                                db_match.home_possession = safe_possession(home_stats_raw.get('Ball Possession'))
                                db_match.away_possession = safe_possession(away_stats_raw.get('Ball Possession'))

                            s_short = status_info.get('short')
                            if s_short in ['1H', '2H', 'ET', 'P', 'LIVE', 'IN_PLAY']:
                                db_match.status = 'Live'
                            elif s_short == 'HT':
                                db_match.status = 'Halftime'
                            elif s_short in ['FT', 'AET', 'PEN', 'FINISHED']:
                                db_match.status = 'FT'
                            elif s_short in ['CANC', 'PST', 'ABD']:
                                db_match.status = 'Postponed'
                            
                            db_match.save()
                            matches_updated += 1
                            self.stdout.write(f"  ✓ [{db_match.elapsed_time}'] {db_match.home_team.name} {db_match.home_score}x{db_match.away_score} {db_match.away_team.name}")
                        else:
                            # Se o jogo estava como AO VIVO no banco, mas sumiu da resposta da API, significa que acabou!
                            current_status = str(db_match.status).upper()
                            live_statuses = ['LIVE', 'IN PLAY', 'IN_PLAY', '1H', '2H', 'HT', 'ET', 'P', 'FIRST HALF', 'SECOND HALF', 'HALFTIME', 'EXTRA TIME', 'PENALTY', 'PAUSED']
                            
                            if current_status in live_statuses:
                                db_match.status = 'FT'
                                db_match.save()
                                matches_updated += 1
                                self.stdout.write(f"  🏁 Finalizado/Removido: {db_match.home_team.name} x {db_match.away_team.name}")
                                
                if matches_updated > 0:
                    try:
                        from matches.services.live_radar import LiveRadarService
                        LiveRadarService.take_snapshots_for_active_matches()
                    except:
                        pass
                
                self.stdout.write(self.style.SUCCESS(f"✅ Sincronizou {matches_updated} Jogos Premium Ao Vivo!"))
                
            else:
                self.stdout.write(self.style.ERROR(f"Erro na API: {response.status_code} - {response.text}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
