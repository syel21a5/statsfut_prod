import time
import json
import random
from curl_cffi import requests
from django.core.management.base import BaseCommand
from matches.models import League, Match, Goal, Season
from django.db import transaction
from django.utils import timezone

# Pool de User-Agents para rotação
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

CHROME_VERSIONS = ["chrome110", "chrome116", "chrome119", "chrome120"]

class Command(BaseCommand):
    help = "Extrai estatísticas profundas (escanteios, cartões, gols detalhados) do SofaScore para uma liga e temporada."

    def add_arguments(self, parser):
        parser.add_argument('--league_id', type=int, help='ID da Liga no banco de dados')
        parser.add_argument('--season_year', type=int, help='Ano da temporada (ex: 2024)')
        parser.add_argument('--limit', type=int, default=None, help='Limite de partidas para processar')
        parser.add_argument('--force', action='store_true', help='Processar mesmo se já tiver estatísticas')
        parser.add_argument('--proxy', type=str, help='Proxy no formato http://user:pass@host:port')
        parser.add_argument('--tor', action='store_true', help='Usar proxy Tor (127.0.0.1:9150)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.consecutive_errors = 0
        self.proxy = None

    def _create_session(self):
        """Cria uma nova sessão com User-Agent aleatório e headers ultra-realistas."""
        ua = random.choice(USER_AGENTS)
        # Escolhe uma versão do Chrome para simular
        impersonate_version = random.choice(["chrome110", "chrome116", "chrome119", "chrome120", "chrome124"])
        self.session = requests.Session(impersonate=impersonate_version)
        
        # Extrai a versão do Chrome do UA para o header sec-ch-ua
        chrome_version = impersonate_version.replace("chrome", "")
        if chrome_version == "124":
            full_version = "124.0.6367.201"
        elif chrome_version == "120":
            full_version = "120.0.6099.129"
        else:
            full_version = "119.0.6045.160"
        
        self.session.headers.update({
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
        
        if self.proxy:
            # curl_cffi suporta socks5://, http://, etc.
            self.session.proxies = {"http": self.proxy, "https": self.proxy}
            self.stdout.write(self.style.NOTICE(f"🌐 Usando proxy: {self.proxy}"))

    def fetch_api(self, url):
        try:
            # Delay aleatório (mais conservador se estivermos sendo bloqueados)
            base_delay = 5.0 if self.consecutive_errors == 0 else 12.0
            delay = random.uniform(base_delay, base_delay + 5.0)
            time.sleep(delay)
            
            # Tenta a requisição
            response = self.session.get(url, timeout=25)
            
            if response.status_code == 200:
                self.consecutive_errors = 0  # Reset no contador de erros
                return response.json()
            elif response.status_code == 404:
                return None
            elif response.status_code == 403:
                self.consecutive_errors += 1
                self.stdout.write(self.style.WARNING(
                    f"⚠️ BLOQUEADO (403) - Erro consecutivo #{self.consecutive_errors} (IP do Tor provavelmente manchado)"
                ))
                
                # Se for bloqueado, espera um pouco mais e limpa a sessão para tentar novo impersonate
                time.sleep(random.uniform(10, 20))
                self._create_session()
                
                if self.consecutive_errors >= 3:
                    # Pausa longa: 5 minutos + nova sessão
                    wait_time = 300  # 5 minutos
                    self.stdout.write(self.style.WARNING(
                        f"🛑 Muitos bloqueios! Pausando {wait_time//60} minutos e renovando sessão..."
                    ))
                    time.sleep(wait_time)
                    self._create_session()  # Nova sessão com novo User-Agent
                    self.consecutive_errors = 0
                    
                    # Tenta de novo após a pausa
                    retry_response = self.session.get(url, timeout=20)
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
        league_id = kwargs['league_id']
        season_year = kwargs['season_year']
        limit = kwargs['limit']
        force = kwargs['force']
        self.proxy = kwargs.get('proxy')
        
        if kwargs.get('tor'):
            # Porta 9150 é a padrão do Tor Browser
            self.proxy = "socks5://127.0.0.1:9150"

        self._create_session()

        if not league_id or not season_year:
            self.stdout.write(self.style.ERROR("Você deve fornecer --league_id e --season_year"))
            return

        league = League.objects.filter(id=league_id).first()
        season = Season.objects.filter(year=season_year).first()

        if not league or not season:
            self.stdout.write(self.style.ERROR(f"Liga (ID {league_id}) ou Temporada ({season_year}) não encontrada."))
            return

        # Filtra partidas finalizadas que têm ID do SofaScore
        matches = Match.objects.filter(
            league=league,
            season=season,
            status__in=['Finished', 'FT', 'AET', 'PEN', 'FINISHED'],
            api_id__startswith='sofa_'
        )

        if not force:
            # Pula partidas que já têm escanteios registrados (indicador de que já foram processadas)
            matches = matches.filter(home_corners__isnull=True)

        if limit:
            matches = matches[:limit]

        total = matches.count()
        self.stdout.write(self.style.SUCCESS(f"Iniciando extração profunda para {total} partidas de {league.name} ({season.year})..."))

        stats_updated = 0
        goals_updated = 0

        for idx, match in enumerate(matches, 1):
            sofa_id = match.api_id.replace('sofa_', '')
            self.stdout.write(f"[{idx}/{total}] Processando {match.home_team} x {match.away_team} (SofaID: {sofa_id})")

            # === PAUSA ESTRATÉGICA a cada 40 jogos ===
            if idx > 1 and idx % 40 == 0:
                pause = random.randint(90, 150)  # 1.5 a 2.5 minutos
                self.stdout.write(self.style.WARNING(
                    f"☕ Pausa estratégica de {pause}s após {idx} jogos... ({stats_updated} atualizados até agora)"
                ))
                time.sleep(pause)
                self._create_session()  # Renova sessão

            # 1. Estatísticas (Escanteios, Cartões, Chutes)
            stats_url = f"https://api.sofascore.com/api/v1/event/{sofa_id}/statistics"
            stats_data = self.fetch_api(stats_url)
            
            if stats_data and 'statistics' in stats_data:
                stats_list = stats_data['statistics']
                if stats_list:
                    # SofaScore geralmente tem grupos: "ALL", "1st half", "2nd half"
                    # Pegamos o "ALL" que é o primeiro
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

                            if name == 'Corner kicks':
                                match.home_corners = h_val
                                match.away_corners = a_val
                            elif name == 'Yellow cards':
                                match.home_yellow = h_val
                                match.away_yellow = a_val
                            elif name == 'Red cards':
                                match.home_red = h_val
                                match.away_red = a_val
                            elif name == 'Shots on target':
                                match.home_shots_on_target = h_val
                                match.away_shots_on_target = a_val
                            elif name == 'Total shots':
                                match.home_shots = h_val
                                match.away_shots = a_val
                            elif name == 'Fouls':
                                match.home_fouls = h_val
                                match.away_fouls = a_val
                    
                    match.save()
                    stats_updated += 1

            # 2. Incidentes (Gols e autores)
            incidents_url = f"https://api.sofascore.com/api/v1/event/{sofa_id}/incidents"
            inc_data = self.fetch_api(incidents_url)
            
            if inc_data and 'incidents' in inc_data:
                # incidentClass: 'goal'
                goals_list = [i for i in inc_data['incidents'] if i.get('incidentClass') == 'goal']
                
                if goals_list:
                    # Limpa gols antigos para evitar duplicidade
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
            f"✅ Concluído! {stats_updated} jogos com estatísticas e {goals_updated} jogos com detalhes de gols."
        ))
