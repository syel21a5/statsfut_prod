import os
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from matches.models import League, Season, Team, Match, LeagueStanding
from matches.utils_odds_api import resolve_team
from matches.services.sofascore_tor import SofaScoreTorService, SOFA_LEAGUE_IDS
from matches.services.sofascore_tor import SOFA_LEAGUE_ID_COUNTRY

# ============================================================================
# 11/08/2026: Standings agora via SofaScore (Tor). API-Football desligada
# (assinatura expira 17/08 e o Van mandou não usar). Busca a classificação
# oficial de cada liga monitorada no SofaScore e grava no banco.
# ============================================================================


class Command(BaseCommand):
    help = "Atualiza a tabela de classificação oficial via SofaScore (Tor). API-Football desligada."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Atualiza a tabela para todas as ligas monitoradas")
        parser.add_argument("--smart", action="store_true", help="Atualiza apenas ligas com jogos nas últimas 24h")
        parser.add_argument("--league_id", type=int, default=None, help="(mantido p/ compat, não usado)")

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando Atualização de Classificação (Standings) via SofaScore/Tor"))

        # Liga -> unique-tournament do SofaScore
        # Usa SOFA_LEAGUE_ID_COUNTRY (que tem (nome, país) → tids) para
        # desambiguar ligas com mesmo nome em países diferentes
        # (ex: "Super League" Suíça vs Grécia; "Premier League" Ucrânia).
        target = []
        seen_ids = set()

        for (l_name, l_country), tids in SOFA_LEAGUE_ID_COUNTRY.items():
            db_league = League.objects.filter(name__iexact=l_name, country=l_country).first()
            if not db_league:
                continue
            if db_league.id in seen_ids:
                continue
            target.append({'tids': tids, 'db_obj': db_league})
            seen_ids.add(db_league.id)

        # Fallback por nome apenas (cobre ligas não listadas no mapping por país)
        for l_name, tids in SOFA_LEAGUE_IDS.items():
            db_league = League.objects.filter(name__iexact=l_name).first() or League.objects.filter(name__icontains=l_name).first()
            if db_league and db_league.id not in seen_ids:
                target.append({'tids': tids, 'db_obj': db_league})
                seen_ids.add(db_league.id)

        if options.get("smart"):
            yesterday = timezone.now() - timedelta(days=1)
            recent_league_ids = Match.objects.filter(date__gte=yesterday).values_list('league_id', flat=True).distinct()
            target = [t for t in target if t['db_obj'].id in recent_league_ids]

        if not target:
            self.stdout.write(self.style.WARNING("Nenhuma liga para processar."))
            return

        svc = SofaScoreTorService()
        svc._create_session()
        BASE = "https://www.sofascore.com/api/v1"

        def _parse_season_year(season_name):
            """Extrai o ano de término da temporada a partir do nome da season do SofaScore.
            Ex: 'Premier League 26/27' -> 2027 | 'Brasileiro Serie A 2026' -> 2026"""
            s = (season_name or "").strip()
            import re
            m = re.search(r'(\d{4})/(\d{2,4})', s) or re.search(r'(\d{2})/(\d{2})', s) or re.search(r'(\d{4})', s)
            if not m:
                return timezone.now().year
            groups = [g for g in m.groups() if g]
            if len(groups) >= 2:
                end = groups[-1]
                return (2000 + int(end)) if int(end) < 100 else int(end)
            return int(groups[-1])

        for league_data in target:
            db_league = league_data['db_obj']
            tids = league_data['tids']

            self.stdout.write(f"\n--> Buscando Standings: {db_league.name} (torneio {tids})")

            for tid in tids:
                try:
                    seasons_r = svc._fetch(f"{BASE}/unique-tournament/{tid}/seasons")
                    if not seasons_r:
                        continue
                    seasons_list = seasons_r.get("seasons", []) or []
                    if not seasons_list:
                        continue
                    sid = seasons_list[0].get("id")
                    # Ano de término derivado do nome da season (ex: '26/27' -> 2027)
                    league_season = _parse_season_year(seasons_list[0].get("name"))
                    db_season, _ = Season.objects.get_or_create(year=league_season)
                    self.stdout.write(f"  Temporada SofaScore: {seasons_list[0].get('name')} -> year={league_season}")

                    data = svc._fetch(f"{BASE}/unique-tournament/{tid}/season/{sid}/standings/total")
                    if not data:
                        # Tenta standings (chave alternativa)
                        data = svc._fetch(f"{BASE}/unique-tournament/{tid}/season/{sid}/standings")
                    if not data:
                        self.stdout.write(self.style.WARNING(f"  Sem standings disponíveis (torneio {tid})."))
                        continue

                    groups = data.get("standings") or []
                    standings_to_create = []
                    for group in groups:
                        rows = group.get("rows") or []
                        for row in rows:
                            team_info = row.get("team") or {}
                            team_name = team_info.get("name") or ""
                            db_team = resolve_team(team_name, db_league)
                            if not db_team:
                                print(f"⚠️ AVISO: Time da classificação não encontrado no banco: '{team_name}'")
                                continue
                            points = row.get("points") or 0
                            played = row.get("matches") or row.get("played") or 0
                            wins = row.get("wins") or 0
                            draws = row.get("draws") or 0
                            losses = row.get("losses") or 0
                            gf = row.get("scoresFor") or 0
                            ga = row.get("scoresAgainst") or 0
                            group_name = group.get("name")

                            standings_to_create.append(LeagueStanding(
                                league=db_league, season=db_season, team=db_team,
                                position=row.get("position") or 0, played=played,
                                won=wins, drawn=draws, lost=losses,
                                goals_for=gf, goals_against=ga, points=points,
                                group_name=group_name,
                            ))

                    if standings_to_create:
                        with transaction.atomic():
                            LeagueStanding.objects.filter(league=db_league, season=db_season).delete()
                            LeagueStanding.objects.bulk_create(standings_to_create)
                        self.stdout.write(self.style.SUCCESS(
                            f"Tabela de {db_league.name} atualizada com {len(standings_to_create)} times (via SofaScore)."
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(f"  Nenhuma linha válida para {db_league.name}."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Erro no torneio {tid} ({db_league.name}): {str(e)[:90]}"))
                time.sleep(0.4)

        self.stdout.write(self.style.SUCCESS("Processo Concluído!"))
