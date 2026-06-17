import os
import time
import random
import logging
from datetime import timedelta
from curl_cffi import requests

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction

from matches.models import Match

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Daemon Ao Vivo Secundário via SofaScore (Salva-vidas para ligas menores)"

    def handle(self, *args, **options):
        # 1. Pega a configuração de Proxy do .env
        proxy_url = os.getenv("RESIDENTIAL_PROXY")
        
        # 2. Busca jogos que podem precisar de ajuda do SofaScore
        # Jogos de hoje (começaram há menos de 4 horas ou começam nos próximos 15 min)
        # e que não estão como FT
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
            return # Sem jogos rolando, não gasta proxy.
            
        self.stdout.write(self.style.SUCCESS("🔥 SofaScore: Buscando placares globais..."))

        impersonate_version = random.choice(["chrome110", "chrome116", "chrome119", "chrome120"])
        session = requests.Session(impersonate=impersonate_version)
        
        chrome_version = impersonate_version.replace("chrome", "")
        version_map = {
            "120": "120.0.6099.129", "119": "119.0.6045.160",
            "116": "116.0.5845.96", "110": "110.0.5481.77",
        }
        full_version = version_map.get(chrome_version, "120.0.6099.129")
        ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36"
        
        session.headers.update({
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "sec-ch-ua": f'"Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}", "Not-A.Brand";v="99"',
            "sec-ch-ua-full-version-list": f'"Google Chrome";v="{full_version}", "Chromium";v="{full_version}", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })
        
        if proxy_url:
            session.proxies = {"http": proxy_url, "https": proxy_url}
            self.stdout.write(f"🌐 Usando proxy residencial")
            
        try:
            # 2. Chama a API diretamente
            url = "https://www.sofascore.com/api/v1/sport/football/events/live"
            response = session.get(url, timeout=40)
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                
                matches_updated = 0
                
                with transaction.atomic():
                    for db_match in all_today_matches:
                        db_home = db_match.home_team.name.lower().replace('-', ' ').strip()
                        db_away = db_match.away_team.name.lower().replace('-', ' ').strip()
                        
                        sofa_event = None
                        
                        # Tenta encontrar no pacotão do SofaScore
                        for ev in events:
                            home_team_name = ev.get('homeTeam', {}).get('name', '').lower().replace('-', ' ').strip()
                            away_team_name = ev.get('awayTeam', {}).get('name', '').lower().replace('-', ' ').strip()
                            
                            if (db_home in home_team_name or home_team_name in db_home) and \
                               (db_away in away_team_name or away_team_name in db_away):
                                sofa_event = ev
                                break
                                
                        if sofa_event:
                            # Encontrou o jogo!
                            status_code = sofa_event.get('status', {}).get('code')
                            status_type = sofa_event.get('status', {}).get('type') # inprogress, finished
                            status_description = sofa_event.get('status', {}).get('description') # e.g., "1st half", "45", "HT"
                            
                            home_score = sofa_event.get('homeScore', {}).get('current')
                            away_score = sofa_event.get('awayScore', {}).get('current')
                            
                            # Atualiza placar
                            if home_score is not None:
                                db_match.home_score = home_score
                            if away_score is not None:
                                db_match.away_score = away_score
                                
                            # Atualiza status e tempo
                            if status_type == 'inprogress':
                                db_match.status = 'Live'
                                try:
                                    if str(status_description).isdigit():
                                        db_match.elapsed_time = int(status_description)
                                    elif "HT" in str(status_description):
                                        db_match.status = 'Halftime'
                                        db_match.elapsed_time = 45
                                    else:
                                        # Tempos de acréscimo "45+2"
                                        if '+' in str(status_description):
                                            parts = str(status_description).split('+')
                                            db_match.elapsed_time = int(parts[0]) + int(parts[1])
                                except:
                                    pass
                            elif status_type == 'finished':
                                db_match.status = 'FT'
                                
                            db_match.save()
                            matches_updated += 1
                            self.stdout.write(f"  ✓ SOFASCORE [{(db_match.elapsed_time or '?')}'] {db_match.home_team.name} {db_match.home_score}x{db_match.away_score} {db_match.away_team.name}")
                
                if matches_updated > 0:
                    try:
                        from matches.services.live_radar import LiveRadarService
                        LiveRadarService.take_snapshots_for_active_matches()
                        from django.core.cache import cache
                        cache.clear()
                    except:
                        pass
                
                self.stdout.write(self.style.SUCCESS(f"✅ Sincronizou {matches_updated} Jogos usando SofaScore!"))
            else:
                self.stdout.write(self.style.ERROR(f"Erro SofaScore: {response.status_code} - Provável bloqueio!"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro de conexão com SofaScore: {e}"))
