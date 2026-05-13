import time
import os
import random
import datetime
from curl_cffi import requests
from django.core.management.base import BaseCommand
from matches.models import Match, Goal
from django.db import transaction
from django.utils import timezone

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

class Command(BaseCommand):
    help = "Gerencia inteligentemente a busca de estatísticas profundas via Tor para jogos recentes finalizados."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=15, help='Limite máximo de partidas para processar por vez (padrão: 15)')
        parser.add_argument('--days_back', type=int, default=15, help='Dias para trás para buscar jogos finalizados (padrão: 15)')
        # Tor default port on Linux is 9050
        parser.add_argument('--proxy', type=str, default='socks5://127.0.0.1:9050', help='Proxy do Tor (padrão: socks5://127.0.0.1:9050)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proxy = None
        self.consecutive_errors = 0

    def _create_session(self):
        ua = random.choice(USER_AGENTS)
        impersonate_version = random.choice(["chrome110", "chrome116", "chrome119", "chrome120", "chrome124"])
        self.session = requests.Session(impersonate=impersonate_version)
        
        chrome_version = impersonate_version.replace("chrome", "")
        full_version = "124.0.6367.201" if chrome_version == "124" else ("120.0.6099.129" if chrome_version == "120" else "119.0.6045.160")
        
        self.session.headers.update({
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "sec-ch-ua": f'"Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}", "Not-A.Brand";v="99"',
            "sec-ch-ua-full-version-list": f'"Google Chrome";v="{full_version}", "Chromium";v="{full_version}", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"' if "Windows" in ua else '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })
        
        if self.proxy:
            self.session.proxies = {"http": self.proxy, "https": self.proxy}

    def _restart_tor(self):
        """Reinicia o serviço do Tor no Linux para forçar a troca de IP"""
        self.stdout.write(self.style.WARNING("🔄 Fui bloqueado (403)! Forçando troca de IP (Restartando Tor via systemctl)..."))
        try:
            # Requer permissões root (geralmente como o cron roda na VPS)
            os.system("systemctl restart tor")
            self.stdout.write(self.style.WARNING("⏳ Aguardando 10 segundos para o Tor se reconectar à rede..."))
            time.sleep(10)
            self._create_session() # Nova sessão para limpar os cookies/headers antigos
            self.consecutive_errors = 0
            self.stdout.write(self.style.SUCCESS("✅ Tor reiniciado! Tentando novamente..."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao tentar reiniciar o Tor: {e}"))

    def fetch_api(self, url):
        try:
            delay = random.uniform(8.0, 15.0)
            time.sleep(delay)
            
            response = self.session.get(url, timeout=25)
            
            if response.status_code == 200:
                self.consecutive_errors = 0
                return response.json()
            elif response.status_code == 404:
                return None
            elif response.status_code == 403:
                self.consecutive_errors += 1
                self._restart_tor()
                
                # Tenta de novo APÓS o restart do Tor (1 chance extra)
                retry_response = self.session.get(url, timeout=25)
                if retry_response.status_code == 200:
                    return retry_response.json()
                
                return None
            else:
                self.stdout.write(self.style.ERROR(f"Erro na API {url}: Status {response.status_code}"))
                return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Exceção ao acessar {url}: {e}"))
            return None

    def handle(self, *args, **kwargs):
        self.proxy = kwargs.get('proxy')
        limit = kwargs.get('limit')
        days_back = kwargs.get('days_back')

        self._create_session()

        # Calcula a data limite para buscar os jogos retroativos
        date_limit = timezone.now() - datetime.timedelta(days=days_back)

        # Buscar todos os jogos finalizados dos últimos X dias, 
        # que vieram do sofascore, e que não possuem estatísticas de escanteios
        matches = Match.objects.filter(
            status__in=['Finished', 'FT', 'AET', 'PEN', 'FINISHED'],
            api_id__startswith='sofa_',
            date__gte=date_limit,
            home_corners__isnull=True
        ).order_by('-date') # Mais recentes primeiro
        
        total_found = matches.count()
        if total_found == 0:
            self.stdout.write(self.style.SUCCESS(f"✅ Nenhum jogo recente (últimos {days_back} dias) precisando de Deep Scrape. Dormindo..."))
            return
            
        self.stdout.write(self.style.SUCCESS(f"🔍 Encontrados {total_found} jogos precisando de Deep Scrape. Processando max {limit}..."))

        matches_to_process = matches[:limit]
        
        stats_updated = 0
        goals_updated = 0

        for idx, match in enumerate(matches_to_process, 1):
            sofa_id = match.api_id.replace('sofa_', '')
            self.stdout.write(f"[{idx}/{limit}] Processando {match.home_team} x {match.away_team} (Data: {match.date.strftime('%d/%m/%Y')})")

            # 1. Estatísticas (Escanteios, Cartões, Chutes)
            stats_url = f"https://api.sofascore.com/api/v1/event/{sofa_id}/statistics"
            stats_data = self.fetch_api(stats_url)
            
            if stats_data and 'statistics' in stats_data:
                stats_list = stats_data['statistics']
                if stats_list:
                    all_group = stats_list[0].get('groups', [])
                    for group in all_group:
                        for stat in group.get('statisticsItems', []):
                            name = stat.get('name')
                            h_val = stat.get('home')
                            a_val = stat.get('away')
                            
                            try:
                                h_val = int(str(h_val).replace('%', '').strip()) if h_val is not None else None
                                a_val = int(str(a_val).replace('%', '').strip()) if a_val is not None else None
                            except ValueError: pass

                            if name == 'Corner kicks': match.home_corners, match.away_corners = h_val, a_val
                            elif name == 'Yellow cards': match.home_yellow, match.away_yellow = h_val, a_val
                            elif name == 'Red cards': match.home_red, match.away_red = h_val, a_val
                            elif name == 'Shots on target': match.home_shots_on_target, match.away_shots_on_target = h_val, a_val
                            elif name == 'Total shots': match.home_shots, match.away_shots = h_val, a_val
                            elif name == 'Fouls': match.home_fouls, match.away_fouls = h_val, a_val
                    
                    match.save()
                    stats_updated += 1

            # 2. Incidentes (Gols e autores)
            incidents_url = f"https://api.sofascore.com/api/v1/event/{sofa_id}/incidents"
            inc_data = self.fetch_api(incidents_url)
            
            if inc_data and 'incidents' in inc_data:
                goals_list = [i for i in inc_data['incidents'] if i.get('incidentClass') == 'goal']
                if goals_list:
                    Goal.objects.filter(match=match).delete()
                    with transaction.atomic():
                        for gol in goals_list:
                            minute = gol.get('time')
                            extra = gol.get('addedTime', 0)
                            total_min = minute + (extra or 0)
                            player_name = gol.get('player', {}).get('name', 'Unknown Player')
                            is_home = gol.get('isHome')
                            team = match.home_team if is_home else match.away_team
                            Goal.objects.create(
                                match=match,
                                team=team,
                                player_name=player_name,
                                minute=total_min,
                                is_own_goal=(gol.get('incidentType') == 'ownGoal'),
                                is_penalty=(gol.get('incidentType') == 'penalty')
                            )
                    goals_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Fim do ciclo! {stats_updated} jogos com stats, {goals_updated} com gols."
        ))
