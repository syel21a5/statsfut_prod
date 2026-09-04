import os
import time
import logging
import sys
import unicodedata
from datetime import timedelta
from curl_cffi import requests

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction

from matches.models import Match

logger = logging.getLogger(__name__)


def _strip_accents(s):
    """Remove acentos de uma string para comparação (ex: Guaraní -> Guarani)."""
    return ''.join(
        c for c in unicodedata.normalize('NFKD', s)
        if not unicodedata.category(c).startswith('M')
    )


class Command(BaseCommand):
    """Daemon Ao Vivo RÁPIDO via LiveScore + ESPN (cada ~30s, sem bloqueio, sem Tor).

    Atualiza SOMENTE placar + minuto + status dos jogos hoje/ao vivo.
    Rotação de fontes (30s):
      1. LiveScore (feed global) — cobre quase todas as ligas.
      2. ESPN (scoreboard por liga) — fallback pras ligas que o LiveScore não cobre
         (ex.: Brasileirão, Série B).
    NÃO mexe em estatísticas ricas (posse/chutes/escanteios) — essas ficam
    por conta do rich_data_tor (a cada 2min via SofaScore/Tor).
    """

    help = "Daemon Ao Vivo rápido (30s) via LiveScore+ESPN — só placar/minuto/status"

    # Liga ESPN (code) -> nomes de liga no banco que devem ser cobertos por ela
    ESPN_LEAGUES = [
        ('bra.1', ('Brasileirão', 'Brasileirão Série A')),
        ('bra.2', ('Série B', 'Brasileirão Série B')),
        ('bra.3', ('Série C', 'Brasileirão Série C')),
        ('eng.1', ('Premier League',)),
        ('eng.2', ('Championship',)),
        ('esp.1', ('La Liga',)),
        ('ita.1', ('Serie A',)),
        ('ger.1', ('Bundesliga',)),
        ('fra.1', ('Ligue 1',)),
        ('arg.1', ('Liga Profesional', 'Primera B')),
        ('por.1', ('Primeira Liga',)),
        ('sco.1', ('Premiership',)),
        ('ned.1', ('Eredivisie',)),
        ('tur.1', ('Süper Lig', 'Super Lig')),
        ('usa.1', ('MLS',)),
        ('ecu.1', ('Liga Pro',)),
        ('par.1', ('Primera Division',)),
    ]

    # Para nomes de liga ambíguos, restringe por país (ex: 'Primera Division' existe em vários países)
    ESPN_LEAGUE_COUNTRY = {
        'par.1': 'Paraguai',
    }


    def handle(self, *args, **options):
        # Loop contínuo: roda a cada ~30s enquanto houver jogo ativo.
        while True:
            try:
                self._tick()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ⚠️ Erro no tick: {e}"))
            # 30 segundos entre execuções
            time.sleep(30)

    def _tick(self):
        # 1. Busca jogos que podem precisar de ajuda (hoje ± 24h, não finalizados)
        today_start = now() - timedelta(hours=24)
        today_end = now() + timedelta(hours=24)

        all_today_matches = Match.objects.filter(
            date__gte=today_start,
            date__lte=today_end
        ).exclude(status__in=['FT', 'AET', 'PEN', 'FINISHED']).select_related('home_team', 'away_team').distinct()

        is_there_active_game = False
        for m in all_today_matches:
            if m.status in ['Scheduled', 'Not Started', 'Timed', 'NS', 'Postponed']:
                if m.date:
                    time_diff_hours = (now() - m.date).total_seconds() / 3600.0
                    if -0.25 <= time_diff_hours <= 3.0:
                        is_there_active_game = True
                        break
            else:
                # É um jogo Live
                is_there_active_game = True
                break

        if not is_there_active_game:
            # Sem jogo ativo — dorme o ciclo e volta
            return

        date_str = now().strftime("%Y%m%d")
        url = f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{date_str}/7?MD=1"

        session = requests.Session(impersonate="chrome120")
        proxy_url = os.getenv("RESIDENTIAL_PROXY")

        try:
            response = session.get(url, timeout=20)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Falha rede LiveScore: {e}"))
            return

        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Erro LiveScore: {response.status_code}"))
            return

        data = response.json()
        stages = data.get('Stages', [])
        events = []
        for stage in stages:
            events.extend(stage.get('Events', []))

        matches_updated = 0
        updated_ids = set()
        with transaction.atomic():
            for db_match in all_today_matches:
                db_home = db_match.home_team.name.lower().replace('-', ' ').strip()
                db_away = db_match.away_team.name.lower().replace('-', ' ').strip()

                livescore_event = None
                for ev in events:
                    home_team_name = ev.get("T1", [{}])[0].get("Nm", "").lower().replace('-', ' ').strip()
                    away_team_name = ev.get("T2", [{}])[0].get("Nm", "").lower().replace('-', ' ').strip()
                    if not home_team_name or not away_team_name:
                        continue
                    # Match flexível (substring) — igual ao live_score_livescore
                    if (db_home in home_team_name or home_team_name in db_home) and \
                       (db_away in away_team_name or away_team_name in db_away):
                        livescore_event = ev
                        break

                if not livescore_event:
                    continue

                status_str = livescore_event.get('Eps', '?')
                h_score = livescore_event.get('Tr1', '')
                a_score = livescore_event.get('Tr2', '')

                # Atualiza placar
                try:
                    if h_score and h_score.isdigit():
                        db_match.home_score = int(h_score)
                    if a_score and a_score.isdigit():
                        db_match.away_score = int(a_score)
                except Exception:
                    pass

                # Atualiza status/minuto
                if status_str in ['FT', 'AET', 'AP']:
                    db_match.status = 'FT'
                elif status_str == 'HT':
                    db_match.status = 'Halftime'
                    db_match.elapsed_time = 45
                elif "'" in status_str:
                    db_match.status = 'Live'
                    clean_time = status_str.replace("'", "")
                    try:
                        if '+' in clean_time:
                            parts = clean_time.split('+')
                            db_match.elapsed_time = int(parts[0]) + int(parts[1])
                        else:
                            db_match.elapsed_time = int(clean_time)
                    except Exception:
                        pass

                db_match.save()
                matches_updated += 1
                updated_ids.add(db_match.id)
                # Marca quando o LiveScore atualizou este jogo — usado pelo rich_data_tor
                # para NÃO sobrescrever o placar dos jogos que o LiveScore cobre (30s).
                try:
                    import json
                    sd = db_match.statistics_data or {}
                    if isinstance(sd, str):
                        try:
                            sd = json.loads(sd)
                        except Exception:
                            sd = {}
                    elif not isinstance(sd, dict):
                        sd = {}
                    sd['live_score_ts'] = int(time.time())
                    db_match.statistics_data = sd
                    db_match.save(update_fields=['statistics_data'])
                except Exception:
                    pass
                self.stdout.write(
                    f"  ⚡ [{(db_match.elapsed_time or '?')}'] {db_match.home_team.name} {db_match.home_score}x{db_match.away_score} {db_match.away_team.name} ({db_match.status})"
                )

        # ---- Fallback ESPN (liga por liga) pras partidas que o LiveScore não cobriu ----
        espn_updated = self._update_from_espn(all_today_matches, updated_ids)
        matches_updated += espn_updated


        if matches_updated > 0:
            try:
                from django.core.cache import cache
                cache.clear()
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(f"✅ Fast-Live 30s: {matches_updated} jogos atualizados"))

    # ------------------------------------------------------------------
    # Fallback ESPN: scoreboard por liga (sem Tor, 30s)
    # Cobre ligas que o LiveScore não traz (ex.: Brasileirão, Série B).
    # ------------------------------------------------------------------
    def _update_from_espn(self, all_today_matches, updated_ids):
        """Atualiza via ESPN as partidas que o LiveScore não cobriu. Retorna quantas atualizou."""
        pendentes = [m for m in all_today_matches if m.id not in updated_ids]
        if not pendentes:
            return 0

        # Liga do banco -> código ESPN
        def _espn_code(db_league):
            for code, names in self.ESPN_LEAGUES:
                if db_league.name in names:
                    req_country = self.ESPN_LEAGUE_COUNTRY.get(code)
                    if req_country and db_league.country != req_country:
                        continue
                    return code
            return None

        # Agrupa pendentes por código ESPN
        por_codigo = {}
        for m in pendentes:
            code = _espn_code(m.league)
            if code:
                por_codigo.setdefault(code, []).append(m)

        if not por_codigo:
            return 0

        date_str = now().strftime("%Y%m%d")
        session = requests.Session(impersonate="chrome120")
        atualizados = 0

        for code, matches in por_codigo.items():
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={date_str}"
            try:
                response = session.get(url, timeout=15)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Falha rede ESPN {code}: {e}"))
                continue
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Erro ESPN {code}: {response.status_code}"))
                continue

            try:
                data = response.json()
                events = data.get('events', [])
            except Exception:
                continue

            for db_match in matches:
                db_home = db_match.home_team.name.lower().replace('-', ' ').strip()
                db_away = db_match.away_team.name.lower().replace('-', ' ').strip()

                ev = None
                for e in events:
                    comps = e.get('competitions', [{}])[0].get('competitors', [])
                    if len(comps) < 2:
                        continue
                    h = comps[0].get('team', {}).get('displayName', '').lower().replace('-', ' ').strip()
                    a = comps[1].get('team', {}).get('displayName', '').lower().replace('-', ' ').strip()
                    if not h or not a:
                        continue
                    if (db_home in h or h in db_home) and (db_away in a or a in db_away):
                        ev = e
                        break

                if not ev:
                    continue

                comp = ev.get('competitions', [{}])[0]
                comps = comp.get('competitors', [])
                status_info = comp.get('status', {}).get('type', {})
                state = status_info.get('state', '').lower()  # 'pre' | 'in' | 'post'
                detail = status_info.get('detail', '') or ''

                try:
                    scores = [c.get('score', '') for c in comps]
                    if scores and all(str(s).isdigit() for s in scores):
                        db_match.home_score = int(scores[0])
                        db_match.away_score = int(scores[1])
                except Exception:
                    pass

                if state == 'in':
                    db_match.status = 'Live'
                    # detail: ex. "74'", "HT", "90'+8'"
                    clean = detail.replace("'", "").strip()
                    if clean.upper() in ('HT', 'HALFTIME', 'INTERVALO'):
                        db_match.status = 'Halftime'
                        db_match.elapsed_time = 45
                    elif clean.isdigit():
                        db_match.elapsed_time = int(clean)
                    elif '+' in clean:
                        try:
                            parts = clean.split('+')
                            db_match.elapsed_time = int(parts[0]) + int(parts[1])
                        except Exception:
                            pass
                elif state == 'post':
                    db_match.status = 'FT'

                db_match.save()
                atualizados += 1
                try:
                    import json
                    sd = db_match.statistics_data or {}
                    if isinstance(sd, str):
                        try:
                            sd = json.loads(sd)
                        except Exception:
                            sd = {}
                    elif not isinstance(sd, dict):
                        sd = {}
                    sd['espn_ts'] = int(time.time())
                    db_match.statistics_data = sd
                    db_match.save(update_fields=['statistics_data'])
                except Exception:
                    pass
                self.stdout.write(
                    f"  📺 ESPN [{(db_match.elapsed_time or '?')}'] {db_match.home_team.name} {db_match.home_score}x{db_match.away_score} {db_match.away_team.name} ({db_match.status})"
                )

        if atualizados > 0:
            try:
                from django.core.cache import cache
                cache.clear()
            except Exception:
                pass
            self.stdout.write(self.style.SUCCESS(f"✅ ESPN fallback: {atualizados} jogos atualizados"))
        return atualizados
