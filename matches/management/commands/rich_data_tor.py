import os
import time
import json
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from matches.models import Match, LiveMatchSnapshot

logger = logging.getLogger(__name__)

# Se o LiveScore atualizou o jogo nos últimos N segundos, o rich_data_tor NÃO mexe
# no placar/minuto (só atualiza stats). Evita sobrescrever dado mais fresco do
# daemon 30s com dado possivelmente mais velho do Tor (2min).
LIVESCORE_FRESH_WINDOW = 150  # 2.5 min — cobre o ciclo do Tor (2min) + margem


class Command(BaseCommand):
    """Daemon de dados RICOS via Tor/SofaScore (a cada 3 min).

    Só puxa estatísticas avançadas (posse, chutes, escanteios, pressão/graph)
    para jogos ao vivo. NÃO mexe em placar/minuto/status — isso fica com o
    live_score_fast (30s via LiveScore).
    """

    help = "Tor/Rich data: posse, chutes, escanteios, pressão (3min) — sem mexer no placar"

    def handle(self, *args, **options):
        from matches.services.sofascore_tor import SofaScoreTorService

        svc = SofaScoreTorService()

        # Jogos ao vivo no banco (independente da fonte do placar)
        live_qs = Match.objects.filter(
            status__in=['Live', 'LIVE', '1H', '2H', 'HT', 'ET', 'Halftime'],
            date__lte=timezone.now(),
        ).select_related('home_team', 'away_team')

        if not live_qs.exists():
            return

        self.stdout.write(self.style.SUCCESS(
            f"📡 Rich Data: {live_qs.count()} jogos ao vivo — buscando stats via Tor..."
        ))

        # Pré-carrega o feed ao vivo uma única vez → mapa event_id -> minuto/status
        # O LiveScore não cobre todas as ligas; o SofaScore tem o minuto real de cada jogo.
        live_minute_map = {}
        live_status_map = {}
        try:
            live_feed = svc.get_live_fixtures()
            for f in live_feed:
                if f.get('id') is not None:
                    live_minute_map[int(f['id'])] = f.get('elapsed')
                    live_status_map[int(f['id'])] = f.get('status')
        except Exception:
            pass  # se falhar, segue sem o minuto

        updated = 0
        for m in live_qs:
            eid = None
            if m.api_id and not str(m.api_id).startswith('sofa_'):
                try:
                    eid = int(str(m.api_id))
                except ValueError:
                    eid = None
            if not eid:
                continue

            try:
                # Tenta puxar dados ricos primeiro
                rich = svc.get_match_rich_data(eid)
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠️ Erro rich data {m.home_team.name} x {m.away_team.name}: {e}"
                ))
                continue

            if not rich:
                continue

            # Atualiza só estatísticas — NÃO mexe em home_score/away_score/status/elapsed_time
            m.home_shots = rich['home_shots']
            m.away_shots = rich['away_shots']
            m.home_shots_on_target = rich['home_shots_on_target']
            m.away_shots_on_target = rich['away_shots_on_target']
            m.home_shots_off_target = rich['home_shots_off_target']
            m.away_shots_off_target = rich['away_shots_off_target']
            m.home_corners = rich['home_corners']
            m.away_corners = rich['away_corners']
            m.home_possession = rich['home_possession']
            m.away_possession = rich['away_possession']
            m.home_fouls = rich['home_fouls']
            m.away_fouls = rich['away_fouls']
            m.home_dangerous_attacks = rich.get('home_dangerous_attacks')
            m.away_dangerous_attacks = rich.get('away_dangerous_attacks')
            m.home_big_chances = rich.get('home_big_chances')
            m.away_big_chances = rich.get('away_big_chances')
            # Preserva o marcador do LiveScore (se existir) em vez de sobrescrever
            sd = m.statistics_data or {}
            if isinstance(sd, str):
                try:
                    sd = json.loads(sd)
                except Exception:
                    sd = {}
            elif not isinstance(sd, dict):
                sd = {}
            sd['graph_points'] = rich['graph_points']
            sd['source'] = 'sofascore_tor'
            m.statistics_data = sd

            # Verifica se o LiveScore atualizou este jogo recentemente
            livescore_fresh = False
            try:
                ts = sd.get('live_score_ts')
                if ts and (int(time.time()) - int(ts)) < LIVESCORE_FRESH_WINDOW:
                    livescore_fresh = True
            except Exception:
                livescore_fresh = False

            # SÓ atualiza placar + status + minuto se o LiveScore NÃO cobriu o jogo
            # (ou se o último LiveScore foi há mais de 2.5 min). Jogos cobertos pelo
            # LiveScore (30s) ficam com o dado mais fresco do daemon; o Tor só cuida
            # dos "órfãos" (Áustria, Rússia etc).
            if not livescore_fresh:
                try:
                    result = svc.get_event_result(eid)
                    if result:
                        if result.get('home_score') is not None:
                            m.home_score = result['home_score']
                        if result.get('away_score') is not None:
                            m.away_score = result['away_score']
                        if result.get('status'):
                            m.status = result['status']
                except Exception:
                    pass
                # Atualiza minuto via feed ao vivo (pré-carregado)
                if eid in live_minute_map and live_minute_map[eid] is not None:
                    m.elapsed_time = live_minute_map[eid]
                if eid in live_status_map and live_status_map[eid]:
                    m.status = live_status_map[eid]
            else:
                self.stdout.write(self.style.HTTP_INFO(
                    f"  🟢 {m.home_team.name} x {m.away_team.name}: placar mantido (LiveScore fresco), só stats"
                ))

            m.save()

            # Snapshot para o calculate_pressure
            try:
                LiveMatchSnapshot.objects.create(
                    match=m,
                    minute=m.elapsed_time or 0,
                    home_shots_on_target=rich['home_shots_on_target'],
                    away_shots_on_target=rich['away_shots_on_target'],
                    home_shots_off_target=rich['home_shots_off_target'],
                    away_shots_off_target=rich['away_shots_off_target'],
                    home_corners=rich['home_corners'],
                    away_corners=rich['away_corners'],
                    home_possession=rich['home_possession'],
                    away_possession=rich['away_possession'],
                )
            except Exception:
                pass

            self.stdout.write(
                f"  📡 {m.home_team.name} x {m.away_team.name} | "
                f"escanteios {rich['home_corners']}x{rich['away_corners']} | "
                f"chutes {rich['home_shots']}x{rich['away_shots']} | "
                f"posse {rich['home_possession']}x{rich['away_possession']}"
            )
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Rich Data Tor: {updated} jogos com stats atualizadas"))