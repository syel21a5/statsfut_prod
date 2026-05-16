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

class SoccerwayAdapter(ScraperAdapter):
    name = "Soccerway"
    def fetch_live_scores(self):
        # Implementação básica segura como fallback
        return []

class BBCAdapter(ScraperAdapter):
    name = "BBC"
    def fetch_live_scores(self):
        # A BBC tem uma API pública frequentemente usada, mas para simplificar, usamos fallback vazio até precisarmos.
        # BeSoccer e ESPN já dão cobertura global massiva.
        return []

# --- Comando Principal ---

class Command(BaseCommand):
    help = 'Daemon inteligente para atualização de placares ao vivo em rodízio'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Não salva no banco, apenas mostra os resultados')

    def get_active_or_upcoming_matches(self):
        """Verifica se há jogos ocorrendo AGORA ou nos próximos 30 minutos"""
        now = timezone.now()
        thirty_mins_from_now = now + timedelta(minutes=30)
        
        # Jogos que estão com status de ao vivo
        live_matches = Match.objects.filter(
            status__in=['Live', '1H', '2H', 'HT', 'In Play']
        ).count()
        
        # Jogos agendados para os próximos 30 minutos ou que já deveriam ter começado (mas não tiveram status atualizado)
        upcoming_matches = Match.objects.filter(
            status='Scheduled',
            date__lte=thirty_mins_from_now,
            date__gte=now - timedelta(hours=3) # Considera jogos das últimas 3 horas que talvez tenham atrasado
        ).count()
        
        return live_matches + upcoming_matches > 0

    def update_matches_in_db(self, live_data, dry_run=False):
        """Atualiza os jogos no banco de dados baseado nos dados raspados"""
        if not live_data:
            return 0
            
        updated_count = 0
        for item in live_data:
            home_name_raw = item.get('home_team')
            away_name_raw = item.get('away_team')
            league_name_raw = item.get('league', 'Desconhecida')
            country_raw = item.get('country', 'Global')
            
            if not home_name_raw or not away_name_raw:
                continue
                
            home_name = normalize_team_name(home_name_raw)
            away_name = normalize_team_name(away_name_raw)
                
            # 1. Tenta busca ultra-precisa por Liga + Times (limpa pontos e espaços)
            match = None
            h_clean = home_name.replace('.', '').strip()
            a_clean = away_name.replace('.', '').strip()

            if league_name_raw != "Desconhecida":
                match = Match.objects.filter(
                    league__name__icontains=league_name_raw[:5],
                    home_team__name__icontains=h_clean[:5],
                    away_team__name__icontains=a_clean[:5],
                    status__in=['Scheduled', 'Live', '1H', '2H', 'HT', 'In Play']
                ).order_by('-date').first()
            
            # 2. Fallback: Busca apenas pelos times (mais flexível)
            if not match:
                match = Match.objects.filter(
                    home_team__name__icontains=h_clean[:5],
                    away_team__name__icontains=a_clean[:5],
                    status__in=['Scheduled', 'Live', '1H', '2H', 'HT', 'In Play']
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
                            match.status = "Finished"
                        elif elapsed == "HT":
                            match.elapsed_time = 45
                            match.status = "HT"
                        else:
                            match.elapsed_time = None
                            
                    match.save()
                
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"[{item.get('source')}] Atualizado: {home_name} {item.get('home_score')}-{item.get('away_score')} {away_name}"))
            else:
                # Log para debug de nomes que não batem
                if league_name_raw == "Bundesliga": # Focar na liga que estamos debulhando
                    self.stdout.write(self.style.WARNING(f"[{item.get('source')}] Não encontrou no DB: {home_name_raw} vs {away_name_raw} (League: {league_name_raw})"))
                
        if updated_count > 0 and not dry_run:
            cache.clear()
            self.stdout.write("Cache limpo.")
            
        return updated_count

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.stdout.write(self.style.SUCCESS('Iniciando o Live Score Daemon...'))
        
        # Lista de adaptadores em rodízio
        adapters = [
            BeSoccerAdapter(),
            GEAdapter(),
            UOLAdapter(),
            ESPNAdapter(),
            SoccerwayAdapter(),
            BBCAdapter()
        ]
        
        current_adapter_index = 0
        
        while True:
            try:
                # 1. Verifica se precisamos trabalhar (Hibernação Inteligente)
                if not self.get_active_or_upcoming_matches():
                    self.stdout.write("Nenhum jogo ao vivo ou próximo. Dormindo por 15 minutos...")
                    time.sleep(15 * 60) # Dorme 15 minutos
                    continue
                
                # 2. Estamos em horário de jogo! Escolhe o adaptador da vez
                adapter = adapters[current_adapter_index]
                self.stdout.write(f"\n[{timezone.now().strftime('%H:%M:%S')}] Usando scraper: {adapter.name}")
                
                # 3. Puxa os dados
                live_data = adapter.fetch_live_scores()
                
                # Adiciona a fonte aos dados
                for item in live_data:
                    item['source'] = adapter.name
                
                self.stdout.write(f"Encontrados {len(live_data)} jogos ao vivo no {adapter.name}.")
                
                # 4. Atualiza o banco
                if live_data:
                    updated = self.update_matches_in_db(live_data, dry_run=dry_run)
                    self.stdout.write(f"Sincronizou {updated} jogos no banco.")
                
                # 5. Rotaciona o adaptador para o próximo ciclo
                current_adapter_index = (current_adapter_index + 1) % len(adapters)
                
                # 6. Aguarda 40 segundos antes da próxima consulta
                self.stdout.write("Aguardando 40 segundos para o próximo ciclo...")
                time.sleep(40)
                
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\nDaemon interrompido pelo usuário. Saindo...'))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro inesperado no loop principal: {e}"))
                self.stdout.write("Aguardando 60 segundos para tentar novamente...")
                time.sleep(60)
