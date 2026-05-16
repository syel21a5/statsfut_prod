import time
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.cache import cache
from matches.models import Match, League
from matches.utils import normalize_team_name

# Configuração de logging
logger = logging.getLogger(__name__)
# Configuração de Proxy para o Tor
TOR_PROXIES = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

class ScraperAdapter:
    """Classe base para os raspadores de placar ao vivo"""
    name = "BaseAdapter"
    use_tor = False
    
    def fetch_live_scores(self):
        """Deve retornar uma lista de dicionários com:
        home_team, away_team, home_score, away_score, status, elapsed, league, country
        """
        raise NotImplementedError()

# --- Adaptadores ---
# Serão implementados nas próximas etapas

class BeSoccerAdapter(ScraperAdapter):
    name = "BeSoccer"
    use_tor = True # BeSoccer bloqueia rápido, Tor é essencial aqui
    
    def fetch_live_scores(self):
        from curl_cffi import requests as requests_cffi
        from bs4 import BeautifulSoup
        
        url = "https://www.besoccer.com/livescore"
        session = requests_cffi.Session(impersonate="chrome120")
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/122.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/"
        })

        try:
            # Tenta usar Tor se habilitado
            proxies = TOR_PROXIES if self.use_tor else None
            response = session.get(url, timeout=30, proxies=proxies)
            if response.status_code != 200:
                logger.error(f"BeSoccer retornou status {response.status_code} (Tor: {self.use_tor})")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            payload = []

            match_links = soup.select('a.match-link')
            
            for match in match_links:
                try:
                    if match.find_parent(class_='autocomplete-box'):
                        continue

                    status_tag = match.select_one('.tag-nobg.live') or match.select_one('.tag-nobg.end')
                    if not status_tag:
                        continue 

                    is_live = 'live' in status_tag.get('class', [])
                    status_text = status_tag.get_text(strip=True)
                    elapsed = status_text.replace("'", "") if is_live else status_text
                    
                    home_team = match.select_one('.team_left').get_text(strip=True) if match.select_one('.team_left') else None
                    away_team = match.select_one('.team_right').get_text(strip=True) if match.select_one('.team_right') else None
                    
                    if not home_team or not away_team:
                        continue

                    home_score = match.select_one('.r1').get_text(strip=True) if match.select_one('.r1') else "0"
                    away_score = match.select_one('.r2').get_text(strip=True) if match.select_one('.r2') else "0"

                    # Detecção avançada de Liga e País
                    league_name = "Desconhecida"
                    country = "Global"
                    parent_panel = match.find_parent(class_='panel')
                    if parent_panel:
                        title_tag = parent_panel.select_one('.comp-title') or \
                                    parent_panel.select_one('.head-title') or \
                                    parent_panel.select_one('.panel-title') or \
                                    parent_panel.select_one('.title')
                        if title_tag:
                            league_name = title_tag.get_text(strip=True)
                            flag = title_tag.find_previous('img', class_='flag') or parent_panel.select_one('img.flag')
                            if flag and flag.get('alt'):
                                country = flag.get('alt')

                    payload.append({
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_score': home_score,
                        'away_score': away_score,
                        'status': 'Live' if is_live else 'Finished',
                        'elapsed': elapsed,
                        'league': league_name,
                        'country': country
                    })
                except Exception:
                    continue

            return payload

        except Exception as e:
            logger.error(f"Erro no BeSoccerAdapter: {e}")
            return []

class GEAdapter(ScraperAdapter):
    name = "GloboEsporte"
    use_tor = False # GE bloqueia Tor geralmente
    def fetch_live_scores(self):
        from curl_cffi import requests as requests_cffi
        from bs4 import BeautifulSoup
        
        url = "https://ge.globo.com/futebol/"
        session = requests_cffi.Session(impersonate="chrome120")
        try:
            response = session.get(url, timeout=15)
            if response.status_code != 200: return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            payload = []
            
            matches = soup.select('.placar-jogo') or soup.select('.match-box')
            for match in matches:
                try:
                    home = match.select_one('.equipe-mandante .equipe-sigla') or match.select_one('.placar-jogo-equipes-mandante-nome')
                    away = match.select_one('.equipe-visitante .equipe-sigla') or match.select_one('.placar-jogo-equipes-visitante-nome')
                    score_home = match.select_one('.placar-jogo-equipes-placar-mandante')
                    score_away = match.select_one('.placar-jogo-equipes-placar-visitante')
                    
                    if not (home and away and score_home and score_away): continue
                    
                    payload.append({
                        'home_team': home.get_text(strip=True),
                        'away_team': away.get_text(strip=True),
                        'home_score': score_home.get_text(strip=True),
                        'away_score': score_away.get_text(strip=True),
                        'status': 'Live',
                        'elapsed': '45',
                        'league': 'Brasileirão',
                        'country': 'Brasil'
                    })
                except Exception:
                    continue
            return payload
        except Exception as e:
            logger.error(f"Erro no GEAdapter: {e}")
            return []

class UOLAdapter(ScraperAdapter):
    name = "UOL"
    def fetch_live_scores(self):
        from curl_cffi import requests as requests_cffi
        from bs4 import BeautifulSoup
        
        url = "https://www.uol.com.br/esporte/futebol/"
        session = requests_cffi.Session(impersonate="chrome120")
        try:
            response = session.get(url, timeout=15)
            if response.status_code != 200: return []
            soup = BeautifulSoup(response.text, 'html.parser')
            payload = []
            
            matches = soup.select('.match-card') or soup.select('.placar')
            for match in matches:
                try:
                    teams = match.select('.team-name')
                    scores = match.select('.team-score')
                    if len(teams) >= 2 and len(scores) >= 2:
                        payload.append({
                            'home_team': teams[0].get_text(strip=True),
                            'away_team': teams[1].get_text(strip=True),
                            'home_score': scores[0].get_text(strip=True),
                            'away_score': scores[1].get_text(strip=True),
                            'status': 'Live',
                            'elapsed': '45'
                        })
                except Exception:
                    continue
            return payload
        except Exception as e:
            logger.error(f"Erro no UOLAdapter: {e}")
            return []

class ESPNAdapter(ScraperAdapter):
    name = "ESPN"
    def fetch_live_scores(self):
        import requests
        
        # O ESPN tem uma API aberta e muito robusta
        url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                logger.error(f"ESPN retornou status {response.status_code}")
                return []
                
            data = response.json()
            events = data.get('events', [])
            
            payload = []
            for event in events:
                try:
                    status_info = event.get('status', {})
                    status_type = status_info.get('type', {})
                    state = status_type.get('state') # pre, in, post
                    
                    if state == 'pre':
                        continue # Pula jogos que não começaram
                        
                    competitions = event.get('competitions', [])
                    if not competitions:
                        continue
                        
                    competitors = competitions[0].get('competitors', [])
                    if len(competitors) < 2:
                        continue
                        
                    # O ESPN geralmente coloca o time da casa no índice 0, mas podemos checar o 'homeAway'
                    home_team_data = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
                    away_team_data = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])
                    
                    home_team = home_team_data.get('team', {}).get('name')
                    away_team = away_team_data.get('team', {}).get('name')
                    home_score = home_team_data.get('score', '0')
                    away_score = away_team_data.get('score', '0')
                    
                    # Decifrar o tempo de jogo
                    elapsed = "FT" if state == 'post' else status_info.get('displayClock', '0')
                    
                    payload.append({
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_score': home_score,
                        'away_score': away_score,
                        'status': 'Finished' if state == 'post' else 'Live',
                        'elapsed': elapsed.replace("'", "")
                    })
                except Exception:
                    continue
                    
            return payload
            
        except Exception as e:
            logger.error(f"Erro no ESPNAdapter: {e}")
            return []

class SofaScoreAdapter(ScraperAdapter):
    name = "SofaScore"
    use_tor = True  # SofaScore bloqueia IPs de VPS, Tor é essencial
    
    def fetch_live_scores(self):
        from curl_cffi import requests as requests_cffi
        
        url = "https://api.sofascore.com/api/v1/sport/football/events/live"
        session = requests_cffi.Session(impersonate="chrome120")
        session.headers.update({
            'Accept': 'application/json',
            'Referer': 'https://www.sofascore.com/',
            'Origin': 'https://www.sofascore.com'
        })
        
        try:
            proxies = TOR_PROXIES if self.use_tor else None
            response = session.get(url, timeout=25, proxies=proxies)
            if response.status_code != 200:
                logger.error(f"SofaScore retornou status {response.status_code}")
                return []
            
            data = response.json()
            events = data.get('events', [])
            payload = []
            
            for event in events:
                try:
                    # ID do evento SofaScore (chave para busca no banco)
                    event_id = str(event.get('id', ''))
                    if not event_id:
                        continue
                    
                    # Status do jogo
                    status_info = event.get('status', {})
                    status_code = status_info.get('code', 0)
                    
                    # Códigos SofaScore: 6=1H, 7=2H, 8=FT, 31=HT, etc.
                    live_codes = [6, 7, 31, 41, 42, 43, 44]
                    finished_codes = [8, 9, 10, 11, 12]
                    
                    if status_code not in live_codes and status_code not in finished_codes:
                        continue
                    
                    home_team_data = event.get('homeTeam', {})
                    away_team_data = event.get('awayTeam', {})
                    
                    home_name = home_team_data.get('name', '')
                    away_name = away_team_data.get('name', '')
                    
                    if not home_name or not away_name:
                        continue
                    
                    home_score = event.get('homeScore', {}).get('current', 0)
                    away_score = event.get('awayScore', {}).get('current', 0)
                    
                    # Calcular minutos de jogo com precisão
                    elapsed = '0'
                    if status_code == 31:
                        elapsed = 'HT'
                    elif status_code in finished_codes:
                        elapsed = 'FT'
                    else:
                        # Tenta calcular a minutagem real
                        import time as time_mod
                        current_ts = event.get('time', {}).get('currentPeriodStartTimestamp')
                        if current_ts:
                            now_ts = int(time_mod.time())
                            mins_in_period = (now_ts - current_ts) // 60
                            if status_code == 7:  # 2H
                                elapsed = str(45 + mins_in_period)
                            else:
                                elapsed = str(mins_in_period)
                        else:
                            elapsed = status_info.get('description', '0')
                    
                    # Liga e país
                    tournament = event.get('tournament', {})
                    league_name = tournament.get('name', 'Desconhecida')
                    country_name = tournament.get('category', {}).get('name', 'Global')
                    
                    is_live = status_code in live_codes
                    
                    payload.append({
                        'sofa_id': event_id,
                        'home_team': home_name,
                        'away_team': away_name,
                        'home_score': str(home_score),
                        'away_score': str(away_score),
                        'status': 'Live' if is_live else 'FT',
                        'elapsed': elapsed,
                        'league': league_name,
                        'country': country_name
                    })
                except Exception:
                    continue
            
            return payload
            
        except Exception as e:
            logger.error(f"Erro no SofaScoreAdapter: {e}")
            return []

class SoccerwayAdapter(ScraperAdapter):
    name = "Soccerway"
    def fetch_live_scores(self):
        return []

class BBCAdapter(ScraperAdapter):
    name = "BBC"
    def fetch_live_scores(self):
        return []

# --- Comando Principal ---

class Command(BaseCommand):
    help = 'Daemon inteligente para atualização de placares ao vivo v2.0'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Não salva no banco, apenas mostra os resultados')

    def get_active_or_upcoming_matches(self):
        """Verifica se há jogos ocorrendo AGORA ou nos próximos 30 minutos"""
        now = timezone.now()
        thirty_mins_from_now = now + timedelta(minutes=30)
        
        live_matches = Match.objects.filter(
            status__in=['Live', '1H', '2H', 'HT', 'In Play', 'LIVE']
        ).count()
        
        upcoming_matches = Match.objects.filter(
            status='Scheduled',
            date__lte=thirty_mins_from_now,
            date__gte=now - timedelta(hours=3)
        ).count()
        
        return live_matches + upcoming_matches > 0

    def update_matches_sofascore(self, live_data, dry_run=False):
        """Atualiza jogos usando api_id do SofaScore — 100% de precisão, zero erro de nome"""
        if not live_data:
            return 0
            
        updated_count = 0
        for item in live_data:
            sofa_id = item.get('sofa_id')
            if not sofa_id:
                continue
            
            match_api_id = f"sofa_{sofa_id}"
            
            # Busca DIRETA por api_id — sem necessidade de adivinhar nomes
            match = Match.objects.filter(api_id=match_api_id).first()
            
            if match:
                if not dry_run:
                    match.home_score = item.get('home_score')
                    match.away_score = item.get('away_score')
                    match.status = item.get('status', 'Live')
                    
                    elapsed = item.get('elapsed')
                    try:
                        match.elapsed_time = int(elapsed)
                    except (ValueError, TypeError):
                        if elapsed == "FT":
                            match.elapsed_time = 90
                            match.status = "FT"
                        elif elapsed == "HT":
                            match.elapsed_time = 45
                            match.status = "HT"
                        else:
                            match.elapsed_time = None
                            
                    match.save()
                
                updated_count += 1
                home_name = match.home_team.name if match.home_team else '?'
                away_name = match.away_team.name if match.away_team else '?'
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ {home_name} {item.get('home_score')}-{item.get('away_score')} {away_name} ({item.get('elapsed', '')}min)"
                ))
                
        if updated_count > 0 and not dry_run:
            cache.clear()
            self.stdout.write("Cache limpo.")
            
        return updated_count

    def update_matches_by_name(self, live_data, dry_run=False):
        """Atualiza jogos buscando por nome de time (fallback para ESPN/BeSoccer)"""
        if not live_data:
            return 0
            
        updated_count = 0
        for item in live_data:
            home_name_raw = item.get('home_team')
            away_name_raw = item.get('away_team')
            
            if not home_name_raw or not away_name_raw:
                continue
                
            home_name = normalize_team_name(home_name_raw)
            away_name = normalize_team_name(away_name_raw)
            
            h_clean = home_name.replace('.', '').strip()
            a_clean = away_name.replace('.', '').strip()

            match = Match.objects.filter(
                home_team__name__icontains=h_clean[:5],
                away_team__name__icontains=a_clean[:5],
                status__in=['Scheduled', 'Live', '1H', '2H', 'HT', 'In Play', 'LIVE']
            ).order_by('-date').first()
            
            if match:
                if not dry_run:
                    match.home_score = item.get('home_score')
                    match.away_score = item.get('away_score')
                    match.status = item.get('status', 'Live')
                    
                    elapsed = item.get('elapsed')
                    try:
                        match.elapsed_time = int(elapsed)
                    except (ValueError, TypeError):
                        if elapsed == "FT":
                            match.elapsed_time = 90
                            match.status = "FT"
                        elif elapsed == "HT":
                            match.elapsed_time = 45
                            match.status = "HT"
                        else:
                            match.elapsed_time = None
                            
                    match.save()
                
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ [{item.get('source')}] {home_name} {item.get('home_score')}-{item.get('away_score')} {away_name}"
                ))
                
        if updated_count > 0 and not dry_run:
            cache.clear()
            self.stdout.write("Cache limpo.")
            
        return updated_count

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.stdout.write(self.style.SUCCESS('Iniciando o Live Score Daemon v2.0...'))
        self.stdout.write('Estratégia: SofaScore (api_id) → ESPN (fallback) → BeSoccer (fallback)')
        self.stdout.write('Intervalo: 30 segundos entre ciclos')
        
        # Fontes
        sofascore = SofaScoreAdapter()
        espn = ESPNAdapter()
        besoccer = BeSoccerAdapter()
        
        # Fontes brasileiras (complementares, rodam a cada 3 ciclos)
        br_adapters = [GEAdapter(), UOLAdapter()]
        br_index = 0
        cycle_count = 0
        
        while True:
            try:
                # 1. Verifica se precisamos trabalhar
                if not self.get_active_or_upcoming_matches():
                    self.stdout.write("Nenhum jogo ao vivo ou próximo. Dormindo por 15 minutos...")
                    time.sleep(15 * 60)
                    continue
                
                cycle_count += 1
                self.stdout.write(f"\n{'='*50}")
                self.stdout.write(f"[{timezone.now().strftime('%H:%M:%S')}] Ciclo #{cycle_count}")
                
                # 2. SEMPRE tenta SofaScore primeiro (api_id = 100% precisão)
                self.stdout.write("  → SofaScore (primário, busca por api_id)...")
                sofa_data = sofascore.fetch_live_scores()
                
                if sofa_data:
                    for item in sofa_data:
                        item['source'] = 'SofaScore'
                    
                    self.stdout.write(f"  Encontrados {len(sofa_data)} jogos ao vivo no SofaScore.")
                    updated = self.update_matches_sofascore(sofa_data, dry_run=dry_run)
                    self.stdout.write(f"  Sincronizou {updated} jogos via api_id.")
                else:
                    # SofaScore falhou — usa ESPN como fallback
                    self.stdout.write(self.style.WARNING("  ⚠ SofaScore falhou. Usando ESPN como fallback..."))
                    espn_data = espn.fetch_live_scores()
                    
                    if espn_data:
                        for item in espn_data:
                            item['source'] = 'ESPN'
                        self.stdout.write(f"  Encontrados {len(espn_data)} jogos ao vivo no ESPN.")
                        updated = self.update_matches_by_name(espn_data, dry_run=dry_run)
                        self.stdout.write(f"  Sincronizou {updated} jogos via nome.")
                    else:
                        # ESPN também falhou — último recurso: BeSoccer
                        self.stdout.write(self.style.WARNING("  ⚠ ESPN também falhou. Tentando BeSoccer..."))
                        besoccer_data = besoccer.fetch_live_scores()
                        if besoccer_data:
                            for item in besoccer_data:
                                item['source'] = 'BeSoccer'
                            self.stdout.write(f"  Encontrados {len(besoccer_data)} jogos no BeSoccer.")
                            updated = self.update_matches_by_name(besoccer_data, dry_run=dry_run)
                            self.stdout.write(f"  Sincronizou {updated} jogos via nome.")
                        else:
                            self.stdout.write(self.style.ERROR("  ✖ Nenhuma fonte disponível neste ciclo."))
                
                # 3. A cada 3 ciclos, tenta também fontes brasileiras (complementar)
                if cycle_count % 3 == 0:
                    br_adapter = br_adapters[br_index % len(br_adapters)]
                    self.stdout.write(f"  → {br_adapter.name} (complementar BR)...")
                    br_data = br_adapter.fetch_live_scores()
                    if br_data:
                        for item in br_data:
                            item['source'] = br_adapter.name
                        updated = self.update_matches_by_name(br_data, dry_run=dry_run)
                        self.stdout.write(f"  {br_adapter.name}: {updated} jogos BR atualizados.")
                    br_index += 1
                
                # 4. Aguarda 30 segundos (ótimo para apostas ao vivo)
                self.stdout.write("Aguardando 30 segundos...")
                time.sleep(30)
                
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\nDaemon interrompido pelo usuário. Saindo...'))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro inesperado no loop principal: {e}"))
                self.stdout.write("Aguardando 60 segundos para tentar novamente...")
                time.sleep(60)
