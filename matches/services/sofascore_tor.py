"""
SofaScore via Tor — substitui a API-Football no ambiente de TESTE (statsfut2).

Usa curl_cffi (fingerprint TLS de Chrome) + proxy SOCKS5 do Tor (porta 9050),
que é o método validado em 03/08/2026 (exit nodes NL/FR/GB passam no bloqueio).

Uso:
    from matches.services.sofascore_tor import SofaScoreTorService
    svc = SofaScoreTorService()
    fixtures = svc.get_live_fixtures()          # todos os jogos ao vivo do mundo
    fixtures = svc.get_upcoming_fixtures(days=3)  # próximos jogos
"""
import os
import time
import random
import subprocess
from datetime import datetime, timedelta, timezone

from curl_cffi import requests

TOR_PROXY = os.getenv("TOR_PROXY", "socks5h://127.0.0.1:9050")
BASE_URL = "https://www.sofascore.com/api/v1"

# Nome da liga (padrão do projeto) -> IDs unique-tournament no SofaScore
# MAPA COMPLETO (04/08/2026): todas as 53 ligas do banco, validado via API
SOFA_LEAGUE_IDS = {
    # Brasil
    "Brasileirão": [325],                # Brasileirão Betano (Série A)
    "Série B": [390],
    "Série C": [1281],
    "Copa do Brasil": [373, 16600],      # Copa Betano do Brasil (373) / Copa do Brasil (16600)
    # Europa top-5
    "La Liga": [8],
    "Premier League": [17],
    "Serie A": [23],
    "Ligue 1": [34],
    "Bundesliga": [35, 45],             # Alemanha (35) + Áustria (45)
    # Europa (outras)
    "Primeira Liga": [238],              # Liga Portugal Betclic
    "Eredivisie": [37],
    "Süper Lig": [52],
    "Superliga": [39],                  # Dinamarca (Danish Superliga)
    "Super League": [215, 185],          # Suíça (215) + Grécia (185) — desambigua por país
    "Pro League": [38],                  # Bélgica ✅ (ID confirmado 04/08)
    "Championship": [18],                # Inglaterra 2ª divisão
    "Premiership": [36],                 # Escócia
    "Ekstraklasa": [202],                # Polônia
    "First League": [172],               # República Tcheca (Czech First League)
    "Premier Liga": [203],               # Rússia
    "Ukrainian Premier League": [218],  # Ucrânia
    "J1 League": [196],                  # Japão
    "Liga MX": [11621],                  # México
    # América do Sul
    "Liga Profesional": [155],           # Argentina
    "Primera B": [703, 1240],            # Argentina (703 Primera Nacional) + Chile (1240 Liga de Ascenso)
    "Primera A": [11539],                # Colômbia
    "Primera Division": [11653, 11541, 30743],  # Chile (11653) + Paraguai (11541) + Uruguai (30743)
    "Liga 1": [406],                     # Peru
    "Liga Pro": [240],                   # Equador (LigaPro Serie A)
    "Serie B": [10240],                  # Equador (LigaPro Serie B)
    "Copa Libertadores": [384],
    "Copa Sul-Americana": [480],
    # América do Norte
    "MLS": [242],
    "USL Championship": [13363],
    # Nórdicos / outras
    "Eliteserien": [20],                 # Noruega
    "1st Division": [22],                # Noruega 2ª
    "Allsvenskan": [40],                 # Suécia
    "Superettan": [46],                  # Suécia 2ª
    "Veikkausliiga": [41],               # Finlândia
    "Ykkösliiga": [55],                  # Finlândia 2ª
    "Besta deild karla": [188],          # Islândia
    "1. deild": [675],                   # Islândia 2ª
    "A-League Men": [136],               # Austrália
}

# -------------------------------------------------------------------------
# MAPA POR (nome, país) — desambigua ligas com o MESMO nome em países
# diferentes (ex: "Super League" na Suíça e na Grécia; "Bundesliga" na
# Alemanha e na Áustria). Chave = (nome da liga, país no banco).
# Usado pelo recalculate_standings para atualizar TODAS as ligas, mesmo as
# que compartilham nome.
# -------------------------------------------------------------------------
SOFA_LEAGUE_ID_COUNTRY = {
    ("Brasileirão", "Brasil"): [325],
    ("Série B", "Brasil"): [390],
    ("Série C", "Brasil"): [1281],
    ("Copa do Brasil", "Brasil"): [373],
    ("La Liga", "Espanha"): [8],
    ("Premier League", "Inglaterra"): [17],
    ("Serie A", "Italia"): [23],
    ("Ligue 1", "Franca"): [34],
    ("Bundesliga", "Alemanha"): [35],
    ("Bundesliga", "Austria"): [45],
    ("Primeira Liga", "Portugal"): [238],
    ("Eredivisie", "Holanda"): [37],
    ("Süper Lig", "Turquia"): [52],
    ("Superliga", "Dinamarca"): [39],
    ("Super League", "Suica"): [215],
    ("Super League", "Grecia"): [185],
    ("Pro League", "Belgica"): [38],
    ("Championship", "Inglaterra"): [18],
    ("Premiership", "Escocia"): [36],
    ("Ekstraklasa", "Polonia"): [202],
    ("First League", "Republica Tcheca"): [172],
    ("Premier Liga", "Russia"): [203],
    ("Premier League", "Ucrania"): [218],
    ("J1 League", "Japao"): [196],
    ("Liga MX", "Mexico"): [11621],
    ("Liga Profesional", "Argentina"): [155],
    ("Primera B", "Argentina"): [703],
    ("Primera B", "Chile"): [1240],
    ("Primera A", "Colombia"): [11539],
    ("Primera Division", "Chile"): [11653],
    ("Primera Division", "Paraguai"): [11541],
    ("Primera Division", "Uruguai"): [30743],
    ("Liga 1", "Peru"): [406],
    ("Liga Pro", "Equador"): [240],
    ("Serie B", "Equador"): [10240],
    ("Copa Libertadores", "America do Sul"): [384],
    ("Copa Sul-Americana", "America do Sul"): [480],
    ("MLS", "Estados Unidos"): [242],
    ("USL Championship", "Estados Unidos"): [13363],
    ("Eliteserien", "Noruega"): [20],
    ("1st Division", "Noruega"): [22],
    ("Allsvenskan", "Suecia"): [40],
    ("Superettan", "Suecia"): [46],
    ("Veikkausliiga", "Finlandia"): [41],
    ("Ykkösliiga", "Finlandia"): [55],
    ("Besta deild karla", "Islandia"): [188],
    ("1. deild", "Islandia"): [675],
    ("A-League Men", "Australia"): [136],
}


def _fmt_ts(ts):
    """Converte timestamp unix para ISO 8601 (formato esperado pelo update_live_matches)."""
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except Exception:
        return None


class SofaScoreTorService:
    """Cliente SofaScore via Tor com rotação automática de circuito."""

    def __init__(self, proxy=None):
        self.proxy = proxy or TOR_PROXY
        self.session = None
        self.consecutive_errors = 0

    # ---------- infra ----------

    def _create_session(self):
        impersonate = random.choice(["chrome110", "chrome120"])
        self.session = requests.Session(impersonate=impersonate)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/",
            "Cache-Control": "no-cache",
        })
        self.session.proxies = {"http": self.proxy, "https": self.proxy}

    def _rotate_tor(self):
        """Força novo circuito no Tor (novo IP de saída)."""
        try:
            subprocess.run(["systemctl", "reload", "tor"], timeout=10, capture_output=True)
        except Exception:
            pass
        time.sleep(6)

    def _fetch(self, url, retries=3):
        if not self.session:
            self._create_session()
        for attempt in range(retries):
            try:
                time.sleep(random.uniform(0.5, 1.5))
                r = self.session.get(url, timeout=45)
                if r.status_code == 200:
                    self.consecutive_errors = 0
                    return r.json()
                if r.status_code in (403, 429):
                    # Bloqueio/limite: vale rotacionar Tor e tentar de novo.
                    print(f"  ⚠️ SofaScore {r.status_code} (bloqueio) — rotacionando Tor... ({attempt + 1}/{retries})")
                    self.consecutive_errors += 1
                    self._rotate_tor()
                    self._create_session()
                    continue
                # 4xx (404, 400, 401...) = resposta definitiva (ex.: evento/ID que não
                # existe mais no SofaScore). Rotacionar Tor NÃO vai mudar o 404, então
                # retornamos vazio sem retry para não travar/enxurrar o log e o Tor.
                print(f"  ⚠️ SofaScore HTTP {r.status_code} em {url[:80]} (sem retry: 4xx definitivo)")
                self.consecutive_errors += 1
                return None
            except Exception as e:
                print(f"  ⚠️ SofaScore erro: {str(e)[:80]} — rotacionando Tor...")
                self._rotate_tor()
                self._create_session()
        return None

    # ---------- dados ----------

    def get_live_fixtures(self):
        """Todos os jogos ao vivo do mundo (1 request), no formato padrão do projeto."""
        data = self._fetch(f"{BASE_URL}/sport/football/events/live")
        if not data:
            return []
        events = data.get("events", [])
        return [self._normalize(ev) for ev in events if ev.get("id")]

    def get_upcoming_fixtures(self, days_ahead=7):
        """Próximos jogos das ligas monitoradas (SOFA_LEAGUE_IDS), varrendo os próximos N dias.

        OBS (04/08/2026): o endpoint antigo /sport/football/scheduled-events/{data} foi
        descontinuado pelo SofaScore (404). O formato atual é:
            /unique-tournament/{tid}/season/{sid}/events/next/{page}
        que retorna os próximos eventos do torneio (30 por página).
        """
        fixtures = []
        today = datetime.now(timezone.utc).date()
        max_date = today + timedelta(days=days_ahead)
        # Liga -> id torneio mapeado (valida se ainda existe no SOFA_LEAGUE_IDS)
        seen_tournament_ids = set()
        for league_name, tids in SOFA_LEAGUE_IDS.items():
            for tid in tids:
                if tid in seen_tournament_ids:
                    continue
                seen_tournament_ids.add(tid)
                try:
                    # 1. Temporada atual
                    seasons = self._fetch(f"{BASE_URL}/unique-tournament/{tid}/seasons")
                    if not seasons:
                        continue
                    seasons_list = seasons.get("seasons", []) or []
                    if not seasons_list:
                        continue
                    sid = seasons_list[0].get("id")
                    # 2. Próximos eventos (SofaScore mudou a API: só aceita events/next/0.
                    #    Qualquer page>0 retorna 404. A page 0 já traz todos os próximos do torneio.)
                    data = self._fetch(f"{BASE_URL}/unique-tournament/{tid}/season/{sid}/events/next/0")
                    if data:
                        events = data.get("events", []) or []
                        for ev in events:
                            if not ev.get("id"):
                                continue
                            # Filtra pela janela de datas (hoje .. hoje+days_ahead)
                            st = ev.get("startTimestamp")
                            if not st:
                                continue
                            try:
                                ev_date = datetime.fromtimestamp(int(st), tz=timezone.utc).date()
                            except Exception:
                                continue
                            if today <= ev_date <= max_date:
                                fixtures.append(self._normalize(ev))
                        time.sleep(random.uniform(0.3, 0.7))
                except Exception as e:
                    print(f"  ⚠️ Erro upcoming torneio {tid}: {str(e)[:60]}")
        return fixtures

    def get_event_incidents(self, event_id):
        """Gols/minutos/cartões de um evento."""
        data = self._fetch(f"{BASE_URL}/event/{event_id}/incidents")
        return (data or {}).get("incidents", [])

    def get_event_result(self, event_id):
        """Status + placar atual de UM evento (para saneamento de jogos 'Scheduled'
        que já passaram do horário — o live global só lista jogos em andamento, então
        jogos que começaram e terminaram entre ciclos ficam presos em Scheduled).
        Retorna dict {status, home_score, away_score} ou None em falha."""
        data = self._fetch(f"{BASE_URL}/event/{event_id}")
        if not data:
            return None
        ev = data.get("event") or {}
        st = ev.get("status") or {}
        st_type = str(st.get("type") or "").lower()
        hs = (ev.get("homeScore") or {}).get("current")
        as_ = (ev.get("awayScore") or {}).get("current")
        sofa_to_padrao = {
            "inprogress": "LIVE",
            "finished": "FT",
            "notstarted": "NS",
            "postponed": "PST",
            "cancelled": "CANC",
            "abandoned": "ABD",
            "interrupted": "ABD",
            "timeToBeDefined": "TBD",
        }
        status_out = sofa_to_padrao.get(st_type, str(st.get("code") or st_type or ""))
        return {
            "status": status_out,
            "home_score": hs,
            "away_score": as_,
            "description": st.get("description"),
        }


    def get_match_rich_data(self, event_id):
        """Dados ricos ao vivo: estatísticas (chutes, escanteios, posse) + gráfico de pressão.
        Retorna dict no formato dos campos do Match, ou None em falha.
        Convenção do gráfico: value > 0 = pressão do time da casa; value < 0 = visitante.
        """
        stats_data = self._fetch(f"{BASE_URL}/event/{event_id}/statistics")
        graph_data = self._fetch(f"{BASE_URL}/event/{event_id}/graph")
        if not stats_data and not graph_data:
            return None

        # --- estatísticas (período ALL = acumulado) ---
        stats = {}
        for grupo in (stats_data or {}).get("statistics", []) or []:
            if grupo.get("period") not in ("ALL", "TOTAL"):
                continue
            for g in grupo.get("groups", []) or []:
                for item in g.get("statisticsItems", []) or []:
                    nome = item.get("name", "")
                    stats[nome] = {
                        "home": item.get("home"),
                        "away": item.get("away"),
                    }

        def _int(v):
            try:
                if v is None:
                    return 0
                return int(str(v).replace("%", "").strip())
            except Exception:
                return 0

        rich = {
            "home_shots": _int((stats.get("Total shots") or {}).get("home")),
            "away_shots": _int((stats.get("Total shots") or {}).get("away")),
            "home_shots_on_target": _int((stats.get("Shots on target") or {}).get("home")),
            "away_shots_on_target": _int((stats.get("Shots on target") or {}).get("away")),
            "home_shots_off_target": _int((stats.get("Shots off target") or {}).get("home")),
            "away_shots_off_target": _int((stats.get("Shots off target") or {}).get("away")),
            "home_corners": _int((stats.get("Corner kicks") or {}).get("home")),
            "away_corners": _int((stats.get("Corner kicks") or {}).get("away")),
            "home_possession": _int((stats.get("Ball possession") or {}).get("home")),
            "away_possession": _int((stats.get("Ball possession") or {}).get("away")),
            "home_fouls": _int((stats.get("Fouls") or {}).get("home")),
            "away_fouls": _int((stats.get("Fouls") or {}).get("away")),
            # Ataques perigosos: o SofaScore não expõe "Dangerous attacks" na API REST,
            # mas "Final third entries" (entradas no terço final) é o proxy oficial mais
            # próximo — mede o mesmo conceito (chegada com perigo ao campo ofensivo).
            "home_dangerous_attacks": _int((stats.get("Final third entries") or {}).get("home")),
            "away_dangerous_attacks": _int((stats.get("Final third entries") or {}).get("away")),
            # Grandes chances (Big chances) — ótimo para o radar ao vivo
            "home_big_chances": _int((stats.get("Big chances") or {}).get("home")),
            "away_big_chances": _int((stats.get("Big chances") or {}).get("away")),
            "graph_points": (graph_data or {}).get("graphPoints", []),
        }
        return rich

    def get_event_statistics(self, event_id):
        """Estatísticas (posse, chutes, escanteios...) de um evento."""
        data = self._fetch(f"{BASE_URL}/event/{event_id}/statistics")
        return (data or {}).get("statistics", [])

    def get_event_graph(self, event_id):
        """Gráfico de pressão (attack momentum)."""
        data = self._fetch(f"{BASE_URL}/event/{event_id}/graph")
        return (data or {}).get("graphPoints", [])

    # ---------- normalização ----------

    @staticmethod
    def _normalize(ev):
        status = ev.get("status", {}) or {}
        home = ev.get("homeTeam", {}) or {}
        away = ev.get("awayTeam", {}) or {}
        tournament = ev.get("tournament", {}) or {}
        unique_tournament = tournament.get("uniqueTournament", {}) or {}
        hs = ev.get("homeScore", {}) or {}
        as_ = ev.get("awayScore", {}) or {}

        # Mapeia status do SofaScore para os códigos que o status_map do daemon espera
        # (LIVE, FT, NS, PST, CANC, ABD — maiúsculos, ver update_live_matches.py)
        st = status.get("code")
        st_type = status.get("type")
        sofa_to_padrao = {
            "inprogress": "LIVE",
            "finished": "FT",
            "notstarted": "NS",
            "postponed": "PST",
            "cancelled": "CANC",
            "abandoned": "ABD",
            "interrupted": "ABD",
            "timeToBeDefined": "TBD",
            "live": "LIVE",
        }
        status_out = sofa_to_padrao.get(str(st_type or "").lower(), str(st or st_type or ""))

        # PERÍODO + MINUTO RELATIVO — para o placar ao vivo não “acumular” 45→90→120.
        # Códigos SofaScore: 6=1st half, 8=Intervalo, 7=2nd half, 10=Intervalo ET,
        # 11=ET 1º, 13=ET 2º, (demais durante live = ainda 1º/2º).
        code = status.get("code")
        periodo = ""
        elapsed = status.get("minute")  # minute do SofaScore já vem relativo ao período
        if status_out == "LIVE":
            if code == 6:
                periodo, base = "1H", 0
            elif code == 8:
                periodo, base = "HT", 0
            elif code == 7:
                periodo, base = "2H", 45
            elif code == 31:
                # Intervalo (Halftime) — código 31 no SofaScore. NÃO é 1º tempo!
                periodo, base = "HT", 0
                elapsed = 45
            elif code in (10, 11, 12, 13):
                periodo, base = "ET", 90
            else:
                # sem código claro: assume 1º tempo (código 0/undefined durante 1H)
                periodo, base = "1H", 0
            # se o SofaScore não entregar minute, estima a partir do início do período atual
            if elapsed is None:
                t = ev.get("time") or {}
                cur_ts = t.get("currentPeriodStartTimestamp")
                if cur_ts:
                    try:
                        min_do_periodo = max(0, int((time.time() - int(cur_ts)) / 60))
                        elapsed = min_do_periodo  # relativo ao período (base já aplicada no display)
                    except Exception:
                        elapsed = None
            # SE AINDA SEM MINUTO: estima pela hora de início do jogo (startTimestamp).
            # Garante que o minuto nunca fique travado/None durante uma partida ao vivo.
            if elapsed is None:
                sts = ev.get("startTimestamp")
                if sts:
                    try:
                        minutos_desde_inicio = max(0, int((time.time() - int(sts)) / 60))
                        if code == 7:
                            # 2º tempo: subtrai o intervalo (~15min). cap em 45+45=90.
                            elapsed = max(1, min(45, minutos_desde_inicio - 45 - 15))
                        elif code == 6:
                            elapsed = max(1, min(45, minutos_desde_inicio))
                        elif code == 8:
                            elapsed = 45
                        elif code in (10, 11, 12, 13):
                            elapsed = max(1, min(30, minutos_desde_inicio - 90 - 15))
                        else:
                            elapsed = max(1, min(45, minutos_desde_inicio))
                    except Exception:
                        elapsed = 1
                else:
                    elapsed = 1  # último recurso: nunca deixa None em jogo ao vivo
            # status final em vez de genérico LIVE, para o template saber o período
            if periodo:
                status_out = periodo

        return {
            "source_api": "sofascore",
            "id": ev.get("id"),
            "date": _fmt_ts(ev.get("startTimestamp")),
            "status": status_out,
            "league": unique_tournament.get("name") or tournament.get("name"),
            "league_id": unique_tournament.get("id") or tournament.get("id"),
            "country": (tournament.get("category") or {}).get("name"),
            "home_team": home.get("name"),
            "away_team": away.get("name"),
            "home_team_id": home.get("id"),
            "away_team_id": away.get("id"),
            "home_score": hs.get("current"),
            "away_score": as_.get("current"),
            "elapsed": elapsed,
            "period": periodo,
        }


if __name__ == "__main__":
    import json

    svc = SofaScoreTorService()
    print("Buscando jogos ao vivo via Tor...")
    live = svc.get_live_fixtures()
    print(f"Total ao vivo: {len(live)}")
    for f in live[:5]:
        print(f"  {f['home_team']} {f['home_score']}x{f['away_score']} {f['away_team']} | {f['league']} | {f['status']}")
