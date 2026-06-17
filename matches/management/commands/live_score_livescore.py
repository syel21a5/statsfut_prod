import os
import time
import logging
from datetime import timedelta
from curl_cffi import requests

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction

from matches.models import Match

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Daemon Ao Vivo Secundário via LiveScore (Salva-vidas sem bloqueio)"

    def handle(self, *args, **options):
        # 1. Busca jogos que podem precisar de ajuda
        today_start = now() - timedelta(hours=24)
        today_end = now() + timedelta(hours=24)

        all_today_matches = Match.objects.filter(
            date__gte=today_start,
            date__lte=today_end
        ).exclude(status__in=['FT', 'AET', 'PEN', 'FINISHED']).distinct()
        
        is_there_active_game = False
        for m in all_today_matches:
            if m.status in ['Scheduled', 'Not Started', 'Timed', 'NS', 'Postponed']:
                if m.date:
                    time_diff_hours = (now() - m.date).total_seconds() / 3600.0
                    # Acorda se o jogo começa em 15 min ou começou há no máximo 3 horas
                    if -0.25 <= time_diff_hours <= 3.0:
                        is_there_active_game = True
                        break
            else:
                # É um jogo Live
                is_there_active_game = True
                break
                
        if not is_there_active_game:
            return # Sem jogos rolando, não gasta recursos
            
        self.stdout.write(self.style.SUCCESS("🔥 LiveScore: Buscando placares globais..."))

        session = requests.Session(impersonate="chrome120")
        
        # Pega a data atual no formato YYYYMMDD para a URL do LiveScore
        date_str = now().strftime("%Y%m%d")
        url = f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{date_str}/7?MD=1"
        
        # Fallback de proxy
        proxy_url = os.getenv("RESIDENTIAL_PROXY")
        
        try:
            response = session.get(url, timeout=20)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Falha na rede direta, tentando fallback Proxy: {e}"))
            if proxy_url:
                session.proxies = {"http": proxy_url, "https": proxy_url}
                try:
                    self.stdout.write("🌐 Tentando via Proxy Residencial...")
                    response = session.get(url, timeout=20)
                except Exception as ex:
                    self.stdout.write(self.style.ERROR(f"Erro no Proxy Fallback: {ex}"))
                    return
            else:
                return

        if response.status_code == 200:
            data = response.json()
            stages = data.get('Stages', [])
            
            # Extrai todos os eventos do JSON
            events = []
            for stage in stages:
                events.extend(stage.get('Events', []))
                
            matches_updated = 0
            
            with transaction.atomic():
                for db_match in all_today_matches:
                    # Normaliza nomes do DB para comparação
                    db_home = db_match.home_team.name.lower().replace('-', ' ').strip()
                    db_away = db_match.away_team.name.lower().replace('-', ' ').strip()
                    
                    livescore_event = None
                    
                    # Procura no pacotão do LiveScore
                    for ev in events:
                        home_team_name = ev.get("T1", [{}])[0].get("Nm", "").lower().replace('-', ' ').strip()
                        away_team_name = ev.get("T2", [{}])[0].get("Nm", "").lower().replace('-', ' ').strip()
                        
                        if not home_team_name or not away_team_name: continue
                        
                        # Estratégia de Match Flexível (Substring)
                        if (db_home in home_team_name or home_team_name in db_home) and \
                           (db_away in away_team_name or away_team_name in db_away):
                            livescore_event = ev
                            break
                            
                    if livescore_event:
                        # Extrai dados do LiveScore
                        status_str = livescore_event.get('Eps', '?')
                        h_score = livescore_event.get('Tr1', '')
                        a_score = livescore_event.get('Tr2', '')
                        
                        # Parse Placares
                        try:
                            if h_score and h_score.isdigit(): db_match.home_score = int(h_score)
                            if a_score and a_score.isdigit(): db_match.away_score = int(a_score)
                        except: pass
                        
                        # Parse Status e Minutos
                        if status_str in ['FT', 'AET', 'AP']:
                            db_match.status = 'FT'
                        elif status_str == 'HT':
                            db_match.status = 'Halftime'
                            db_match.elapsed_time = 45
                        elif "'" in status_str: # Ex: "35'" ou "90+2'"
                            db_match.status = 'Live'
                            clean_time = status_str.replace("'", "")
                            try:
                                if '+' in clean_time:
                                    parts = clean_time.split('+')
                                    db_match.elapsed_time = int(parts[0]) + int(parts[1])
                                else:
                                    db_match.elapsed_time = int(clean_time)
                            except: pass
                            
                        db_match.save()
                        matches_updated += 1
                        self.stdout.write(f"  ✓ LIVESCORE [{(db_match.elapsed_time or '?')}'] {db_match.home_team.name} {db_match.home_score}x{db_match.away_score} {db_match.away_team.name} ({db_match.status})")
            
            if matches_updated > 0:
                try:
                    from matches.services.live_radar import LiveRadarService
                    LiveRadarService.take_snapshots_for_active_matches()
                    from django.core.cache import cache
                    cache.clear()
                except:
                    pass
            
            self.stdout.write(self.style.SUCCESS(f"✅ Sincronizou {matches_updated} Jogos usando LiveScore!"))
        else:
            self.stdout.write(self.style.ERROR(f"Erro LiveScore: {response.status_code}"))
