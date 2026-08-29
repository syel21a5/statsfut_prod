import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import League, Match, Season, Team

# ============================================================================
# 11/08/2026: BACKFILL agora é 100% via SofaScore (Tor).
# A API-Football foi desligada (assinatura expira 17/08 e o Van mandou não usar).
# Placar base (Passo 1) e estatísticas/gols (Passo 2) vêm do SofaScoreTorService.
# Estados: mantém a assinatura --league_id/--limit/--season do sync_daily_api.
# ============================================================================


class Command(BaseCommand):
    help = 'Busca fixtures e estatísticas passadas via SofaScore (Tor). API-Football desligada.'

    def add_arguments(self, parser):
        parser.add_argument('--league_id', type=int, required=True, help='ID da liga no banco de dados local.')
        parser.add_argument('--limit', type=int, default=10, help='Limite de chamadas individuais (0 = ilimitado).')
        parser.add_argument('--season', type=int, default=datetime.now().year, help='Ano da temporada (ex: 2026).')

    def handle(self, *args, **options):
        from matches.services.sofascore_tor import SofaScoreTorService, SOFA_LEAGUE_IDS

        league_id_db = options['league_id']
        stat_limit = options['limit']
        season_year = options['season']

        try:
            db_league = League.objects.get(id=league_id_db)
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Liga ID {league_id_db} não encontrada no banco."))
            return

        # Descobre o unique-tournament do SofaScore para esta liga (por nome).
        sofa_ids = SOFA_LEAGUE_IDS.get(db_league.name, [])
        if not sofa_ids:
            self.stdout.write(self.style.WARNING(
                f"'{db_league.name}' não está em SOFA_LEAGUE_IDS — pulando (dados já vêm via update_live)."
            ))
            return

        svc = SofaScoreTorService()
        db_season, _ = Season.objects.get_or_create(year=season_year)
        self.stdout.write(self.style.SUCCESS(
            f"\n[1] Buscando resultados via SofaScore (Tor) da Liga '{db_league.name}' (torneio {sofa_ids})..."
        ))

        # ---------- PASSO 1: placares base ----------
        # Para cada torneio, busca as últimas temporadas/eventos e atualiza placares
        # dos jogos que JÁ existem no banco (caso por confronto home x away + janela de data).
        matched_count = 0
        for tid in sofa_ids:
            try:
                seasons_r = svc._fetch(f"https://www.sofascore.com/api/v1/unique-tournament/{tid}/seasons")
                if not seasons_r:
                    continue
                seasons_list = seasons_r.get("seasons", []) or []
                if not seasons_list:
                    continue
                # SofaScore ordena por temporada; pega a atual (primeira).
                sid = seasons_list[0].get("id")
                # Busca os últimos eventos finalizados dessa temporada (páginas de 30).
                finished = []
                for offset in range(4):
                    data = svc._fetch(
                        f"https://www.sofascore.com/api/v1/unique-tournament/{tid}/season/{sid}/events/last/{offset}"
                    )
                    if not data:
                        break
                    evs = data.get("events", []) or []
                    if not evs:
                        break
                    finished.extend(evs)
                    time.sleep(0.3)

                for ev in finished:
                    st = (ev.get("status") or {}).get("type", "")
                    if str(st).lower() != "finished":
                        continue
                    home = (ev.get("homeTeam") or {}).get("name")
                    away = (ev.get("awayTeam") or {}).get("name")
                    hs = (ev.get("homeScore") or {}).get("current")
                    as_ = (ev.get("awayScore") or {}).get("current")
                    sofa_id = ev.get("id")
                    ts = ev.get("startTimestamp")
                    if not (home and away):
                        continue
                    try:
                        ev_date = datetime.fromtimestamp(int(ts), tz=timezone.utc) if ts else None
                    except Exception:
                        ev_date = None

                    # Casar por confronto no banco (janela de ±3 dias p/ ser seguro).
                    match = None
                    from django.db.models import Q
                    qs = Match.objects.filter(
                        Q(home_team__name__iexact=home) & Q(away_team__name__iexact=away)
                    ) | Match.objects.filter(
                        Q(home_team__name__iexact=away) & Q(away_team__name__iexact=home)
                    )
                    if ev_date:
                        from django.utils import timedelta as _td
                        qs = qs.filter(date__gte=ev_date - _td(days=3), date__lte=ev_date + _td(days=3))
                    match = qs.first()

                    if match:
                        changed = False
                        if hs is not None and match.home_score != hs:
                            match.home_score = hs; changed = True
                        if as_ is not None and match.away_score != as_:
                            match.away_score = as_; changed = True
                        if match.status != 'Finished':
                            match.status = 'Finished'; changed = True
                        if sofa_id:
                            match.api_id = f"sofa_{sofa_id}"; changed = True
                        if changed:
                            try:
                                match.save(update_fields=['home_score', 'away_score', 'status', 'api_id'])
                            except Exception as _dup:
                                # Duas linhas casaram com o mesmo api_id SofaScore (duplicata no banco).
                                # Salva sem o api_id (deixa o dedupe resolver) e segue.
                                try:
                                    match.save(update_fields=['home_score', 'away_score', 'status'])
                                except Exception:
                                    pass
                                self.stdout.write(f"  ⚠️ Duplicata de api_id (pulando id): {home} x {away}")
                            matched_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  ⚠️ Erro no torneio {tid}: {str(e)[:80]}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Placares base atualizados: {matched_count} jogos (via SofaScore)."))

        # ---------- PASSO 2: estatísticas (escanteios) + gols ----------
        self.stdout.write(self.style.SUCCESS(f"\n[2] Inspecionando jogos finalizados sem estatísticas (via SofaScore)..."))
        matches_needs_stats = Match.objects.filter(
            league=db_league,
            season=db_season,
            status__in=['Finished', 'FT', 'AET', 'PEN']
        ).filter(home_corners__isnull=True).order_by('-date')

        total_needs = matches_needs_stats.count()
        self.stdout.write(f"Encontrados {total_needs} jogos que precisam de escanteios.")

        if total_needs == 0:
            self.stdout.write(self.style.SUCCESS("Todos os jogos finalizados já possuem estatísticas! Nada a fazer."))
            return

        if stat_limit > 0:
            matches_needs_stats = matches_needs_stats[:stat_limit]

        stats_fetched = 0
        from matches.models import Goal
        for match in matches_needs_stats:
            api_id_str = str(match.api_id or '')
            # Extrai o id numérico do SofaScore (sofa_XXXXXX) para a consulta.
            sofa_id = api_id_str.replace('sofa_', '').strip()
            if not sofa_id.isdigit():
                self.stdout.write(f"  -> Sem ID SofaScore válido (pulando): {match.home_team.name} x {match.away_team.name} (api_id={api_id_str})")
                continue

            try:
                rich = svc.get_match_rich_data(sofa_id)
                if rich:
                    if (rich.get('home_corners') is not None and rich.get('away_corners') is not None):
                        match.home_corners = rich['home_corners']
                        match.away_corners = rich['away_corners']
                        match.save(update_fields=['home_corners', 'away_corners'])

                # Gols via incidents
                incidents = svc.get_event_incidents(sofa_id) or []
                if incidents:
                    match.goals.all().delete()
                    goals_saved = 0
                    for inc in incidents:
                        if (inc.get("incidentType") or "").lower() != 'goal':
                            continue
                        minute = int(inc.get("time") or 0)
                        player = (inc.get("player") or {}).get("name") or "Unknown"
                        scoring_team = None
                        tid = (inc.get("team") or {}).get("id")
                        # O incident vem com team.id; casa com home/away do SofaScore.
                        # Tentamos casa-direta primeiro (time já tem api_id), senão por nome.
                        if tid:
                            scoring_team = Team.objects.filter(api_id=f"sofa_{tid}").first()
                            if scoring_team is None:
                                scoring_team = match.home_team if tid == 0 else None
                        if scoring_team is None:
                            # fallback: casa/fora por ordem do incident quando timestamps casam
                            inc_side = (inc.get("incidentClass") or "")
                            scoring_team = match.home_team if 'home' in str(inc_side).lower() else match.away_team
                        if scoring_team:
                            Goal.objects.create(
                                match=match, team=scoring_team,
                                player_name=player, minute=minute,
                                is_penalty=bool(inc.get("isPenalty")),
                                is_own_goal=bool(inc.get("isOwnGoal")),
                            )
                            goals_saved += 1
                    stats_fetched += 1
                    self.stdout.write(f"      ✓ {match.home_team.name} x {match.away_team.name}: escanteios + {goals_saved} gols")
                else:
                    stats_fetched += 1
                    self.stdout.write(f"      ✓ {match.home_team.name} x {match.away_team.name}: escanteios (sem gols retornados)")
                time.sleep(0.4)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"      ✗ Erro: {str(e)[:80]}"))

        self.stdout.write(self.style.SUCCESS(f"\nFinalizado! {stats_fetched} jogos atualizados com SofaScore (escanteios + gols)."))
