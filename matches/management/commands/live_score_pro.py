import os
import sys
import time
import requests
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction

from matches.models import Match, Team

def smart_name_match(db_name, api_name):
    if not db_name or not api_name:
        return False
    db_clean = db_name.lower().replace('.', '').replace('-', ' ').strip()
    api_clean = api_name.lower().replace('.', '').replace('-', ' ').strip()
    
    if db_clean == api_clean:
        return True
        
    if api_clean in db_clean or db_clean in api_clean:
        return True
        
    db_words = db_clean.split()
    api_words = api_clean.split()
    
    if len(db_words) > 0 and len(api_words) > 0:
        if db_words[-1] == api_words[-1]:
            if db_words[0][0] == api_words[0][0]:
                return True
                
        if len(db_words) == len(api_words):
            match_all = True
            for w1, w2 in zip(db_words, api_words):
                if w1 != w2:
                    if not (w1.startswith(w2) or w2.startswith(w1)):
                        match_all = False
                        break
            if match_all:
                return True
    return False

class Command(BaseCommand):
    help = "Daemon que busca dados ao vivo globais via API-Football (20s interval com Smart Sleep)"

    def handle(self, *args, **options):
        api_key = os.getenv("API_FOOTBALL_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY não configurada no .env!"))
            return

        headers = {
            'x-apisports-key': api_key,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }

        self.stdout.write(self.style.SUCCESS("⚽ Iniciando o Live Score PRO (API-Football) - 20s Loop"))
        
        cycle = 1
        while True:
            # === SMART SLEEP LOGIC ===
            # Checa se temos jogos relevantes (Ao Vivo ou começando em 30 min)
            active_matches = Match.objects.filter(
                status__in=['Live', 'In Play', 'First Half', 'Second Half', 'Halftime', 'Extra Time', 'Penalty']
            )
            
            upcoming_matches = Match.objects.filter(
                status__in=['Scheduled', 'Not Started', 'Timed', 'Postponed'],
                date__lte=now() + timedelta(minutes=30),
                date__gte=now() - timedelta(hours=3) # Não buscar jogos muito velhos "presos"
            )
            
            if not active_matches.exists() and not upcoming_matches.exists():
                self.stdout.write(self.style.WARNING(f"[{datetime.now().strftime('%H:%M:%S')}] Ciclo #{cycle} - NENHUM JOGO ATIVO. Entrando em Smart Sleep por 10 minutos... zZz"))
                time.sleep(600) # 10 minutos
                cycle += 1
                continue
                
            self.stdout.write(self.style.SUCCESS(f"\n[{datetime.now().strftime('%H:%M:%S')}] Ciclo #{cycle} - Iniciando sincronização mundial..."))
            
            try:
                # Busca TODOS os jogos ao vivo no mundo (1 Request)
                url = "https://v3.football.api-sports.io/fixtures?live=all"
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    fixtures = data.get('response', [])
                    self.stdout.write(f"  → API-Football retornou {len(fixtures)} jogos ao vivo no mundo inteiro.")
                    
                    matches_updated = 0

                    # Get candidate matches for today +- 5 hours
                    db_matches = list(Match.objects.filter(
                        date__gte=now() - timedelta(hours=5),
                        date__lte=now() + timedelta(hours=5)
                    ).select_related('home_team', 'away_team'))

                    with transaction.atomic():
                        for fix in fixtures:
                            f_info = fix.get('fixture', {})
                            t_info = fix.get('teams', {})
                            g_info = fix.get('goals', {})
                            status_info = f_info.get('status', {})
                            stats_list = fix.get('statistics', [])
                            
                            f_id = f_info.get('id')
                            home_name = t_info.get('home', {}).get('name')
                            away_name = t_info.get('away', {}).get('name')
                            
                            # Tenta encontrar o jogo na lista de candidatos
                            db_match = None
                            
                            # 1. Tenta mapear pelo api_id se já estiver associado
                            if f_id:
                                for m in db_matches:
                                    if m.api_id == str(f_id):
                                        db_match = m
                                        break
                            
                            # 2. Tenta mapear usando a lógica de nome inteligente
                            if not db_match:
                                for m in db_matches:
                                    if smart_name_match(m.home_team.name, home_name) and smart_name_match(m.away_team.name, away_name):
                                        db_match = m
                                        break
                                        
                            if db_match:
                                # Se o jogo foi encontrado e ainda não tinha o api_id correto da API-Football, salva
                                if f_id and (not db_match.api_id or db_match.api_id.startswith('sofa_')):
                                    db_match.api_id = str(f_id)

                                # Atualiza status e gols
                                db_match.home_score = g_info.get('home') if g_info.get('home') is not None else db_match.home_score
                                db_match.away_score = g_info.get('away') if g_info.get('away') is not None else db_match.away_score
                                db_match.elapsed_time = status_info.get('elapsed')
                                
                                # === PARSE LIVE STATISTICS ===
                                # A API retorna um array com 2 elementos: [home_stats, away_stats]
                                # Cada um contém: {"team": {...}, "statistics": [{"type": "...", "value": ...}, ...]}
                                if stats_list and len(stats_list) >= 2:
                                    home_stats_raw = {}
                                    away_stats_raw = {}
                                    
                                    for stat in stats_list[0].get('statistics', []):
                                        home_stats_raw[stat.get('type', '')] = stat.get('value')
                                    for stat in stats_list[1].get('statistics', []):
                                        away_stats_raw[stat.get('type', '')] = stat.get('value')
                                    
                                    # Helper to safely get int values
                                    def safe_int(val):
                                        if val is None: return None
                                        try: return int(val)
                                        except (ValueError, TypeError): return None
                                    
                                    def safe_possession(val):
                                        if val is None: return None
                                        try: return int(str(val).replace('%', ''))
                                        except (ValueError, TypeError): return None
                                    
                                    # Shots
                                    db_match.home_shots = safe_int(home_stats_raw.get('Total Shots'))
                                    db_match.away_shots = safe_int(away_stats_raw.get('Total Shots'))
                                    db_match.home_shots_on_target = safe_int(home_stats_raw.get('Shots on Goal'))
                                    db_match.away_shots_on_target = safe_int(away_stats_raw.get('Shots on Goal'))
                                    
                                    # Corners
                                    db_match.home_corners = safe_int(home_stats_raw.get('Corner Kicks'))
                                    db_match.away_corners = safe_int(away_stats_raw.get('Corner Kicks'))
                                    
                                    # Fouls
                                    db_match.home_fouls = safe_int(home_stats_raw.get('Fouls'))
                                    db_match.away_fouls = safe_int(away_stats_raw.get('Fouls'))
                                    
                                    # Cards
                                    db_match.home_yellow = safe_int(home_stats_raw.get('Yellow Cards'))
                                    db_match.away_yellow = safe_int(away_stats_raw.get('Yellow Cards'))
                                    db_match.home_red = safe_int(home_stats_raw.get('Red Cards'))
                                    db_match.away_red = safe_int(away_stats_raw.get('Red Cards'))
                                    
                                    # Shots off target
                                    db_match.home_shots_off_target = safe_int(home_stats_raw.get('Shots off Goal'))
                                    db_match.away_shots_off_target = safe_int(away_stats_raw.get('Shots off Goal'))
                                    
                                    # Possession (vem como "55%" da API)
                                    db_match.home_possession = safe_possession(home_stats_raw.get('Ball Possession'))
                                    db_match.away_possession = safe_possession(away_stats_raw.get('Ball Possession'))
                                    
                                    # Dangerous Attacks (Ataques Perigosos)
                                    # A API-Football não tem um campo direto "Dangerous Attacks" mas pode ter "expected_goals"
                                    # Usamos "Blocked Shots" + chutes como proxy se não tiver o campo direto
                                    
                                    # HT Score (da API score section)
                                    score_info = fix.get('score', {})
                                    ht_score = score_info.get('halftime', {})
                                    if ht_score.get('home') is not None:
                                        db_match.ht_home_score = ht_score.get('home')
                                    if ht_score.get('away') is not None:
                                        db_match.ht_away_score = ht_score.get('away')
                                
                                s_short = status_info.get('short')
                                if s_short in ['1H', '2H', 'ET', 'P', 'LIVE']:
                                    db_match.status = 'Live'
                                elif s_short == 'HT':
                                    db_match.status = 'Halftime'
                                elif s_short in ['FT', 'AET', 'PEN']:
                                    db_match.status = 'Finished'
                                elif s_short in ['CANC', 'PST', 'ABD']:
                                    db_match.status = 'Postponed'
                                
                                db_match.save()
                                matches_updated += 1

                    # Tirar snapshot para o Radar de Pressão (após salvar os dados)
                    try:
                        from matches.services.live_radar import LiveRadarService
                        snapshots = LiveRadarService.take_snapshots_for_active_matches()
                        if snapshots > 0:
                            self.stdout.write(f"  📸 Tirou {snapshots} snapshots para o Radar de Pressão.")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"  ⚠ Erro ao tirar snapshots: {e}"))
                                
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Sincronizou {matches_updated} jogos do nosso Radar com a API."))
                    
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ Erro da API: {response.status_code} - {response.text}"))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Erro de conexão/timeout: {e}"))
                
            self.stdout.write("Aguardando 20 segundos...\n" + "="*50)
            time.sleep(20)
            cycle += 1
