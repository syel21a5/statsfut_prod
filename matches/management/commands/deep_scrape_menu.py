"""
Menu interativo para Deep Scrape de estatísticas avançadas por liga.
Baixa escanteios, cartões, chutes, faltas e detalhes de gols para
a temporada atual e a anterior de qualquer liga do banco.

Uso:
  python manage.py deep_scrape_menu
  python manage.py deep_scrape_menu --tor
  python manage.py deep_scrape_menu --league 44          (pula o menu)
  python manage.py deep_scrape_menu --league 44 --limit 5
"""
import time
import random
from curl_cffi import requests
from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from matches.models import League, Season, Match, Goal
from django.db import transaction

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]


class Command(BaseCommand):
    help = "Menu interativo para Deep Scrape de estatísticas avançadas (escanteios, cartões, gols) por liga."

    def add_arguments(self, parser):
        parser.add_argument('--tor', action='store_true', help='Usar proxy Tor (tenta 9050 e 9150)')
        parser.add_argument('--proxy', type=str, default=None, help='Proxy customizado (ex: socks5://127.0.0.1:9050)')
        parser.add_argument('--league', type=int, default=None, help='ID da liga no banco (pula o menu interativo)')
        parser.add_argument('--limit', type=int, default=None, help='Limite de partidas por temporada (padrão: todas)')
        parser.add_argument('--force', action='store_true', help='Reprocessar mesmo partidas que já têm escanteios')
        parser.add_argument('--seasons', type=int, default=2, help='Quantidade de temporadas para processar (padrão: 2 = atual + anterior)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proxy = None
        self.consecutive_errors = 0
        self.session = None

    def _create_session(self):
        """Cria uma nova sessão com User-Agent aleatório."""
        ua = random.choice(USER_AGENTS)
        impersonate_version = random.choice(["chrome110", "chrome116", "chrome119", "chrome120"])
        self.session = requests.Session(impersonate=impersonate_version)

        chrome_version = impersonate_version.replace("chrome", "")
        version_map = {
            "120": "120.0.6099.129",
            "119": "119.0.6045.160",
            "116": "116.0.5845.96",
            "110": "110.0.5481.77",
        }
        full_version = version_map.get(chrome_version, "110.0.5481.77")

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
            self.session.proxies = {"http": self.proxy, "https": self.proxy}

    def _setup_proxy(self, tor=False, proxy=None):
        """Configura o proxy (Tor ou customizado)."""
        if proxy:
            self.proxy = proxy
            self.stdout.write(self.style.SUCCESS(f"🌐 Usando proxy: {self.proxy}"))
        elif tor:
            # Tenta porta 9050 (Docker/Linux) primeiro, depois 9150 (Windows Tor Browser)
            test_session = requests.Session(impersonate="chrome120")
            for port in [9050, 9150]:
                try:
                    test_proxy = f"socks5://127.0.0.1:{port}"
                    test_session.get(
                        "https://api.sofascore.com/api/v1/unique-tournament/35/season/52331/standings/total",
                        proxies={"http": test_proxy, "https": test_proxy},
                        timeout=8
                    )
                    self.proxy = test_proxy
                    self.stdout.write(self.style.SUCCESS(f"🌐 Tor conectado na porta {port}"))
                    return
                except Exception:
                    continue
            self.stdout.write(self.style.WARNING("⚠️ Tor não disponível. Usando conexão direta."))

    def _rotate_tor_ip(self):
        """Tenta enviar sinal de NEWNYM para o Tor para rotacionar o IP."""
        if not self.proxy or "socks5://127.0.0.1" not in self.proxy:
            return False

        # Determina a porta de controle com base na porta socks
        socks_port = 9050
        if "9150" in self.proxy:
            socks_port = 9150
        
        control_port = 9051 if socks_port == 9050 else 9151
        
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(("127.0.0.1", control_port))
            s.sendall(b'AUTHENTICATE ""\r\n')
            response = s.recv(1024)
            if b"250" in response:
                s.sendall(b'SIGNAL NEWNYM\r\n')
                response = s.recv(1024)
                if b"250" in response:
                    self.stdout.write(self.style.SUCCESS(f"🔄 IP do Tor rotacionado com sucesso via porta de controle {control_port}!"))
                    time.sleep(8)  # Pausa de 8 segundos para o Tor estabelecer um circuito estável e seguro
                    s.close()
                    return True
            s.close()
        except Exception:
            pass
        return False

    def fetch_api(self, url):
        """Faz requisição à API com rate limiting e retry."""
        try:
            base_delay = 5.0 if self.consecutive_errors == 0 else 12.0
            delay = random.uniform(base_delay, base_delay + 5.0)
            time.sleep(delay)

            response = self.session.get(url, timeout=25)

            if response.status_code == 200:
                self.consecutive_errors = 0
                return response.json()
            elif response.status_code == 404:
                return None
            elif response.status_code == 403:
                self.consecutive_errors += 1
                self.stdout.write(self.style.WARNING(
                    f"⚠️ BLOQUEADO (403) - Erro #{self.consecutive_errors}"
                ))
                time.sleep(random.uniform(5, 10))
                
                # Tenta rotacionar o IP do Tor!
                self._rotate_tor_ip()
                self._create_session()

                if self.consecutive_errors >= 3:
                    wait_time = 180  # 3 minutos
                    self.stdout.write(self.style.WARNING(
                        f"🛑 Muitos bloqueios! Pausando {wait_time // 60} min..."
                    ))
                    time.sleep(wait_time)
                    self._create_session()
                    self.consecutive_errors = 0

                    retry_response = self.session.get(url, timeout=20)
                    if retry_response.status_code == 200:
                        return retry_response.json()

                return None
            else:
                self.stdout.write(self.style.ERROR(f"Erro {response.status_code}: {url}"))
                return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Exceção: {e}"))
            return None

    def _get_leagues_with_diagnostics(self):
        """Retorna todas as ligas que possuem partidas do SofaScore, com diagnóstico."""
        leagues = League.objects.filter(
            matches__api_id__startswith='sofa_'
        ).distinct().order_by('country', 'name')

        results = []
        for league in leagues:
            # Pega as 2 temporadas mais recentes com jogos desta liga
            seasons = Season.objects.filter(
                matches__league=league
            ).distinct().order_by('-year')[:2]

            season_info = []
            for season in seasons:
                total = Match.objects.filter(
                    league=league, season=season,
                    status__in=['Finished', 'FT', 'AET', 'PEN', 'FINISHED'],
                    api_id__startswith='sofa_'
                ).count()

                with_corners = Match.objects.filter(
                    league=league, season=season,
                    status__in=['Finished', 'FT', 'AET', 'PEN', 'FINISHED'],
                    api_id__startswith='sofa_',
                    home_corners__isnull=False
                ).count()

                pending = total - with_corners
                season_info.append({
                    'season': season,
                    'total': total,
                    'with_corners': with_corners,
                    'pending': pending,
                })

            total_pending = sum(s['pending'] for s in season_info)
            results.append({
                'league': league,
                'seasons': season_info,
                'total_pending': total_pending,
            })

        return results

    def _show_menu(self, league_data):
        """Mostra o menu interativo com diagnóstico de cada liga."""
        self.stdout.write("")
        self.stdout.write("=" * 75)
        self.stdout.write("  🎯 DEEP SCRAPE MENU - Estatísticas Avançadas (Escanteios, Cartões, Gols)")
        self.stdout.write("=" * 75)
        self.stdout.write("")
        self.stdout.write(f"  {'#':<4} {'Liga':<35} {'Pendente':<10} {'Temporadas'}")
        self.stdout.write("  " + "-" * 70)

        for idx, data in enumerate(league_data, 1):
            league = data['league']
            name = f"{league.country} - {league.name}"
            if len(name) > 33:
                name = name[:30] + "..."

            seasons_str = " | ".join([
                f"{s['season'].year}: {s['pending']}/{s['total']}"
                for s in data['seasons']
            ])

            pending = data['total_pending']
            if pending > 0:
                status = f"⚠️  {pending}"
            else:
                status = "✅ 0"

            self.stdout.write(f"  {idx:<4} {name:<35} {status:<10} {seasons_str}")

        self.stdout.write("")
        self.stdout.write("  " + "-" * 70)
        self.stdout.write(f"  {'0':<4} {'TODAS as ligas pendentes':<35}")
        self.stdout.write("")

    def _process_league(self, league, num_seasons=2, limit=None, force=False):
        """Processa o deep scrape para uma liga específica."""
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"{'=' * 60}"))
        self.stdout.write(self.style.SUCCESS(f"  🏆 Processando: {league.country} - {league.name} (ID: {league.id})"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 60}"))

        # Pega as N temporadas mais recentes
        seasons = Season.objects.filter(
            matches__league=league
        ).distinct().order_by('-year')[:num_seasons]

        if not seasons:
            self.stdout.write(self.style.WARNING("Nenhuma temporada encontrada para esta liga."))
            return

        total_stats = 0
        total_goals = 0

        for season in seasons:
            stats, goals = self._deep_scrape_season(league, season, limit, force)
            total_stats += stats
            total_goals += goals

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ {league.country} - {league.name} finalizado! "
            f"{total_stats} jogos com stats, {total_goals} com gols detalhados."
        ))

    def _deep_scrape_season(self, league, season, limit=None, force=False):
        """Executa o deep scrape para uma liga/temporada específica."""
        self.stdout.write(self.style.WARNING(
            f"\n  📅 Temporada {season.year} ───────────────────────"
        ))

        matches = Match.objects.filter(
            league=league,
            season=season,
            status__in=['Finished', 'FT', 'AET', 'PEN', 'FINISHED'],
            api_id__startswith='sofa_'
        )

        if not force:
            matches = matches.filter(home_corners__isnull=True)

        if limit:
            matches = matches[:limit]

        total = matches.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("  ✅ Todas as partidas já possuem dados detalhados!"))
            return 0, 0

        self.stdout.write(f"  📊 {total} partidas para processar...")

        stats_updated = 0
        goals_updated = 0

        for idx, match in enumerate(matches, 1):
            sofa_id = match.api_id.replace('sofa_', '')
            self.stdout.write(
                f"  [{idx}/{total}] {match.home_team} x {match.away_team} "
                f"({match.date.strftime('%d/%m/%Y') if match.date else '?'})"
            )

            # Pausa estratégica a cada 40 jogos
            if idx > 1 and idx % 40 == 0:
                pause = random.randint(90, 150)
                self.stdout.write(self.style.WARNING(
                    f"  ☕ Pausa de {pause}s após {idx} jogos... ({stats_updated} atualizados)"
                ))
                time.sleep(pause)
                self._create_session()

            # 1. ESTATÍSTICAS (Escanteios, Cartões, Chutes, Faltas)
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
                            except ValueError:
                                pass

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

            # 2. INCIDENTES (Gols detalhados)
            incidents_url = f"https://api.sofascore.com/api/v1/event/{sofa_id}/incidents"
            inc_data = self.fetch_api(incidents_url)

            if inc_data and 'incidents' in inc_data:
                goals_list = [i for i in inc_data['incidents'] if i.get('incidentType') == 'goal']
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
            f"  ✅ Temporada {season.year}: {stats_updated} stats + {goals_updated} gols"
        ))
        return stats_updated, goals_updated

    def handle(self, *args, **kwargs):
        use_tor = kwargs.get('tor', False)
        proxy = kwargs.get('proxy')
        league_id = kwargs.get('league')
        limit = kwargs.get('limit')
        force = kwargs.get('force', False)
        num_seasons = kwargs.get('seasons', 2)

        # Setup proxy/Tor
        self._setup_proxy(tor=use_tor, proxy=proxy)
        self._create_session()

        # Se passou --league, pula o menu
        if league_id:
            league = League.objects.filter(id=league_id).first()
            if not league:
                self.stdout.write(self.style.ERROR(f"Liga ID {league_id} não encontrada!"))
                return
            self._process_league(league, num_seasons=num_seasons, limit=limit, force=force)
            return

        # Menu interativo
        league_data = self._get_leagues_with_diagnostics()

        if not league_data:
            self.stdout.write(self.style.ERROR("Nenhuma liga com partidas do SofaScore encontrada no banco."))
            return

        self._show_menu(league_data)

        try:
            choice = input("  Escolha o número da liga (ou 0 para todas): ").strip()
            choice = int(choice)
        except (ValueError, EOFError):
            self.stdout.write(self.style.ERROR("Opção inválida."))
            return

        if choice == 0:
            # Processar todas as ligas que têm partidas pendentes
            pending_leagues = [d for d in league_data if d['total_pending'] > 0]
            if not pending_leagues:
                self.stdout.write(self.style.SUCCESS("✅ Todas as ligas já estão com dados completos!"))
                return

            self.stdout.write(self.style.SUCCESS(
                f"\n🚀 Processando {len(pending_leagues)} ligas pendentes..."
            ))
            for data in pending_leagues:
                self._process_league(data['league'], num_seasons=num_seasons, limit=limit, force=force)

        elif 1 <= choice <= len(league_data):
            selected = league_data[choice - 1]
            self._process_league(selected['league'], num_seasons=num_seasons, limit=limit, force=force)
        else:
            self.stdout.write(self.style.ERROR(f"Opção {choice} inválida."))
            return

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  🏁 DEEP SCRAPE CONCLUÍDO!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
