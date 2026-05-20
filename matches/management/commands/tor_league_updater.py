"""
tor_league_updater.py
=====================
Comando Django para atualizar ligas secundárias (2ª divisão etc.)
diretamente na VPS usando o Tor como proxy.

Funcionalidades:
- Busca dados do SofaScore via Tor (porta 9050)
- Rotação automática de IP ao detectar bloqueio (403 / timeout)
- Importa o payload e recalcula standings automaticamente
- Suporta múltiplas ligas secundárias em um único comando

Uso:
    ./venv/bin/python manage.py tor_league_updater
    ./venv/bin/python manage.py tor_league_updater --league championship
    ./venv/bin/python manage.py tor_league_updater --full-scan
"""

import json
import time
import os
import random
from curl_cffi import requests
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League, Season

# ============================================================
# CONFIGURAÇÃO DAS LIGAS SECUNDÁRIAS
# Adicione novas ligas secundárias aqui conforme forem sendo
# integradas ao sistema.
# ============================================================
SECONDARY_LEAGUES = [
    {
        "key": "championship",
        "tournament_id": 18,
        "season_id": 76986,
        "name": "Championship",
        "country": "Inglaterra",
        "division": 2,
        "year": 2026,
    },
    # Para adicionar mais ligas secundárias, basta copiar o bloco acima e preencher:
    # {
    #     "key": "serie_b_brasil",
    #     "tournament_id": XXX,
    #     "season_id": XXXXX,
    #     "name": "Série B",
    #     "country": "Brasil",
    #     "division": 2,
    #     "year": 2026,
    # },
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]


class Command(BaseCommand):
    help = "Atualiza ligas secundárias na VPS usando Tor como proxy para burlar bloqueios do SofaScore."

    def add_arguments(self, parser):
        parser.add_argument('--league', type=str, default=None,
                            help='Chave da liga específica para atualizar (ex: championship). Se omitido, atualiza todas.')
        parser.add_argument('--full-scan', action='store_true',
                            help='Buscar todas as rodadas (mais lento). Padrão: apenas últimas 3 rodadas.')
        parser.add_argument('--proxy', type=str, default='socks5h://127.0.0.1:9050',
                            help='Proxy do Tor (padrão: socks5h://127.0.0.1:9050)')
        parser.add_argument('--max-retries', type=int, default=3,
                            help='Máximo de rotações de IP por liga (padrão: 3)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None
        self.proxy = None
        self.consecutive_errors = 0
        self.max_retries = 3

    def _create_session(self):
        """Cria uma nova sessão HTTP com fingerprint aleatório e proxy Tor."""
        ua = random.choice(USER_AGENTS)
        impersonate = random.choice(["chrome110", "chrome116", "chrome119", "chrome120"])
        self.session = requests.Session(impersonate=impersonate)
        self.session.headers.update({
            "User-Agent": ua,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/",
            "Cache-Control": "no-cache",
        })
        if self.proxy:
            self.session.proxies = {"http": self.proxy, "https": self.proxy}

    def _rotate_tor_ip(self):
        """Força o Tor a trocar de circuito (IP) quando detecta bloqueio."""
        self.stdout.write(self.style.WARNING("🔄 Bloqueio detectado! Forçando troca de IP do Tor..."))
        try:
            # Método 1: SIGHUP (troca circuito sem reiniciar o processo)
            result = os.system("killall -HUP tor 2>/dev/null || pkill -HUP tor 2>/dev/null")
            if result != 0:
                # Método 2: Reiniciar o serviço completo
                os.system("systemctl restart tor 2>/dev/null")

            wait_time = random.uniform(8, 15)
            self.stdout.write(self.style.WARNING(f"⏳ Aguardando {wait_time:.0f}s para o Tor reconectar..."))
            time.sleep(wait_time)

            # Recria a sessão com novos headers/fingerprint
            self._create_session()
            self.consecutive_errors = 0

            # Verifica se o novo IP funciona
            try:
                test_resp = self.session.get("https://api.ipify.org?format=json", timeout=15)
                if test_resp.status_code == 200:
                    new_ip = test_resp.json().get('ip', '???')
                    self.stdout.write(self.style.SUCCESS(f"✅ Novo IP do Tor: {new_ip}"))
                    return True
            except:
                pass

            self.stdout.write(self.style.WARNING("⚠️ Tor reconectou mas não conseguiu verificar IP."))
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao rotacionar Tor: {e}"))
            return False

    def fetch_api(self, url, sleep_range=(1.5, 4.0)):
        """Faz uma requisição à API com rate limiting e retry automático com rotação de IP."""
        delay = random.uniform(*sleep_range)
        time.sleep(delay)

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=20)

                if response.status_code == 200:
                    self.consecutive_errors = 0
                    return response.json()
                elif response.status_code == 404:
                    return None
                elif response.status_code == 403:
                    self.consecutive_errors += 1
                    self.stdout.write(self.style.ERROR(f"❌ 403 Forbidden em {url}"))
                    if attempt < self.max_retries:
                        self._rotate_tor_ip()
                        time.sleep(random.uniform(2, 5))
                        continue
                    return None
                else:
                    self.stdout.write(self.style.ERROR(f"Erro {response.status_code} em {url}"))
                    return None
            except Exception as e:
                self.consecutive_errors += 1
                self.stdout.write(self.style.ERROR(f"Exceção em {url}: {e}"))
                if attempt < self.max_retries:
                    self._rotate_tor_ip()
                    time.sleep(random.uniform(2, 5))
                    continue
                return None
        return None

    def scrape_league(self, league_config, full_scan=False):
        """Raspa dados de uma liga secundária do SofaScore (mesmo formato do master_fetcher)."""
        t_id = league_config["tournament_id"]
        s_id = league_config["season_id"]

        self.stdout.write(f"\n🔍 Raspando {league_config['name']} ({league_config['country']})...")

        payload = {
            "tournament_id": t_id,
            "season_id": s_id,
            "standings": None,
            "rounds": []
        }

        # 1. Standings
        st_url = f"https://api.sofascore.com/api/v1/unique-tournament/{t_id}/season/{s_id}/standings/total"
        standings_data = self.fetch_api(st_url)
        if standings_data:
            payload['standings'] = standings_data

        # 2. Torneios extras (sub-torneios como Playoffs)
        tournaments_to_scrape = [(t_id, "Regular Season", True)]
        if standings_data and 'standings' in standings_data:
            for group in standings_data['standings']:
                sub_id = group.get('tournament', {}).get('id')
                sub_name = group.get('name', 'Group')
                if sub_id and sub_id != t_id:
                    if not any(t[0] == sub_id for t in tournaments_to_scrape):
                        tournaments_to_scrape.append((sub_id, sub_name, False))

        # 2b. CupTrees
        ct_url = f"https://api.sofascore.com/api/v1/unique-tournament/{t_id}/season/{s_id}/cuptrees"
        ct_data = self.fetch_api(ct_url)
        if ct_data and "cupTrees" in ct_data:
            for tree in ct_data["cupTrees"]:
                sub_t = tree.get("tournament", {})
                sub_id = sub_t.get("id")
                sub_name = sub_t.get("name", "Playoffs")
                if sub_id and sub_id != t_id:
                    if not any(t[0] == sub_id for t in tournaments_to_scrape):
                        tournaments_to_scrape.append((sub_id, sub_name, False))

        # 3. Rodadas
        for tid, label, is_unique in tournaments_to_scrape:
            self.stdout.write(f"  >>> Raspando {label}...")
            prefix = "unique-tournament" if is_unique else "tournament"
            r_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/rounds"
            rounds_data = self.fetch_api(r_url)

            events_count = 0
            if rounds_data and 'rounds' in rounds_data:
                all_rounds = rounds_data['rounds']

                # No modo inteligente, pega apenas as últimas 3 rodadas
                if not full_scan:
                    all_rounds = all_rounds[-3:]
                    self.stdout.write(f"  (Modo inteligente: apenas últimas {len(all_rounds)} rodadas)")

                for round_info in all_rounds:
                    r_num = round_info['round']
                    self.stdout.write(f"  Rodada {r_num}...")
                    e_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/events/round/{r_num}"
                    events_data = self.fetch_api(e_url)
                    events = events_data.get('events', []) if events_data else []
                    if events:
                        events_count += len(events)
                        payload['rounds'].append({
                            "round_label": label,
                            "round_number": r_num,
                            "events": events
                        })

            # Fallback paginado se não encontrou rodadas
            if events_count == 0:
                self.stdout.write(f"  ⚠️ Sem eventos via /rounds para {label}. Usando fallback paginado...")
                all_events = []
                for page in range(10):
                    url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/events/last/{page}"
                    data = self.fetch_api(url)
                    if not data or not data.get('events'):
                        break
                    all_events.extend(data['events'])
                    if data.get('hasNextPage') == False:
                        break

                for page in range(5):
                    url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/events/next/{page}"
                    data = self.fetch_api(url)
                    if not data or not data.get('events'):
                        break
                    all_events.extend(data['events'])
                    if data.get('hasNextPage') == False:
                        break

                if all_events:
                    rounds_map = {}
                    for ev in all_events:
                        r_num = ev.get('roundInfo', {}).get('round', 1) if ev.get('roundInfo') else 1
                        rounds_map.setdefault(r_num, []).append(ev)
                    for r_num in sorted(rounds_map.keys()):
                        payload['rounds'].append({
                            "round_label": label,
                            "round_number": r_num,
                            "events": rounds_map[r_num]
                        })
                    self.stdout.write(f"  ✅ Fallback coletou {len(all_events)} eventos.")

        total_events = sum(len(r['events']) for r in payload['rounds'])
        self.stdout.write(self.style.SUCCESS(
            f"  📊 Total: {len(payload['rounds'])} blocos, {total_events} eventos coletados."
        ))
        return payload

    def handle(self, *args, **kwargs):
        self.proxy = kwargs.get('proxy')
        self.max_retries = kwargs.get('max_retries', 3)
        league_filter = kwargs.get('league')
        full_scan = kwargs.get('full_scan', False)

        # Filtra ligas se especificado
        leagues_to_update = SECONDARY_LEAGUES
        if league_filter:
            leagues_to_update = [l for l in SECONDARY_LEAGUES if l['key'] == league_filter]
            if not leagues_to_update:
                self.stdout.write(self.style.ERROR(
                    f"Liga '{league_filter}' não encontrada. Disponíveis: {[l['key'] for l in SECONDARY_LEAGUES]}"
                ))
                return

        self._create_session()

        # Verifica conectividade do Tor antes de começar
        self.stdout.write("🌐 Verificando conexão do Tor...")
        try:
            ip_resp = self.session.get("https://api.ipify.org?format=json", timeout=15)
            if ip_resp.status_code == 200:
                tor_ip = ip_resp.json().get('ip', '???')
                self.stdout.write(self.style.SUCCESS(f"✅ Tor conectado! IP: {tor_ip}"))
            else:
                self.stdout.write(self.style.ERROR("❌ Tor não respondeu. Tentando reiniciar..."))
                self._rotate_tor_ip()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Tor indisponível: {e}"))
            self.stdout.write("Tentando reiniciar o Tor...")
            if not self._rotate_tor_ip():
                self.stdout.write(self.style.ERROR("Falha ao conectar ao Tor. Abortando."))
                return

        # Processa cada liga secundária
        for league_config in leagues_to_update:
            self.stdout.write(self.style.SUCCESS(
                f"\n{'='*60}\n🏟️  {league_config['name']} ({league_config['country']}) - Div {league_config['division']}\n{'='*60}"
            ))

            # 1. Garante que a liga existe no banco
            league_obj, created = League.objects.get_or_create(
                name=league_config['name'],
                country=league_config['country'],
                defaults={'division': league_config['division']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Liga '{league_config['name']}' criada no banco!"))

            # 2. Raspa os dados via Tor
            payload = self.scrape_league(league_config, full_scan=full_scan)

            if not payload or len(payload.get('rounds', [])) == 0:
                self.stdout.write(self.style.ERROR(f"❌ Nenhum dado coletado para {league_config['name']}. Pulando..."))
                continue

            # 3. Salva o payload temporário
            payload_filename = f"payload_tor_{league_config['key']}.json"
            with open(payload_filename, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False)
            self.stdout.write(f"💾 Payload salvo em {payload_filename}")

            # 4. Importa o payload no banco
            self.stdout.write("📥 Importando payload no banco de dados...")
            try:
                call_command(
                    'import_sofascore_payload',
                    file=payload_filename,
                    league_name=league_config['name'],
                    country=league_config['country'],
                    season_year=league_config['year']
                )
                self.stdout.write(self.style.SUCCESS(f"✅ Importação concluída para {league_config['name']}!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro na importação: {e}"))
                continue

            # 5. Recalcula standings
            self.stdout.write("📊 Recalculando tabelas...")
            try:
                call_command(
                    'recalculate_standings',
                    league_name=league_config['name'],
                    country=league_config['country'],
                    season_year=league_config['year']
                )
                self.stdout.write(self.style.SUCCESS(f"✅ Tabelas recalculadas para {league_config['name']}!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao recalcular: {e}"))

            # 6. Limpa o arquivo temporário
            try:
                os.remove(payload_filename)
            except:
                pass

        self.stdout.write(self.style.SUCCESS(
            f"\n🎉 Atualização de ligas secundárias concluída! {len(leagues_to_update)} liga(s) processada(s)."
        ))
