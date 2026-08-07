import os
from datetime import timedelta

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import League, Season, Team, Match, Goal


class Command(BaseCommand):
    help = "Importa eventos de gols da Liga Profesional (Argentina) via API-Football para popular o model Goal"

    def add_arguments(self, parser):
        parser.add_argument(
            "--api-league-id",
            type=int,
            required=True,
            help="ID da liga na API-Football (ex: 128 para Liga Profesional)",
        )
        parser.add_argument(
            "--season",
            type=int,
            help="Ano da temporada (ex: 2024 para 2024)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Quantos dias para trás considerar (para evitar varrer a temporada inteira de uma vez)",
        )

    def handle(self, *args, **options):
        # Check global flag
        if not APIManager.USE_API_FOOTBALL:
            self.stdout.write(self.style.WARNING("API-Football está DESATIVADA globalmente (APIManager.USE_API_FOOTBALL = False). Abortando."))
            return

        api_key = (
            os.getenv("API_FOOTBALL_KEY_3")
            or os.getenv("API_FOOTBALL_KEY_1")
            or os.getenv("API_FOOTBALL_KEY_2")
            or os.getenv("API_FOOTBALL_BRASILEIRAO_KEY")
        )
        if not api_key:
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY_1/2 não configurada no .env"))
            return

        api_league_id = options["api_league_id"]
        days_back = options["days"]

        league = League.objects.filter(name__icontains="Liga Profesional", country__icontains="Argentina").first()
        if not league:
            league = League.objects.filter(name__icontains="Liga Profesional").first()
        if not league:
            self.stdout.write(self.style.ERROR("Liga 'Liga Profesional' não encontrada no banco"))
            return

        if options["season"]:
            season_year = options["season"]
            season, _ = Season.objects.get_or_create(year=season_year)
        else:
            season = (
                Season.objects.filter(matches__league=league)
                .distinct()
                .order_by("-year")
                .first()
            )
            if not season:
                self.stdout.write(
                    self.style.ERROR(
                        "Nenhuma Season com jogos encontrada para Liga Profesional"
                    )
                )
                return

        finished_statuses = ["Finished", "FT", "AET", "PEN", "FINISHED"]
        base_qs = Match.objects.filter(
            league=league,
            season=season,
            status__in=finished_statuses,
            date__isnull=False,
        )
        if not base_qs.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"Nenhum jogo finalizado encontrado para Liga Profesional na temporada {season.year}"
                )
            )
            return

        distinct_dates = sorted({m.date.date() for m in base_qs})

        self.stdout.write(
            self.style.SUCCESS(
                f"Importando gols da Liga Profesional (league_id={api_league_id}) "
                f"para a temporada {season.year} ({len(distinct_dates)} datas com jogos)"
            )
        )
        
        self.stdout.write(f"DEBUG: Using API Key starting with {api_key[:4]}...")

        headers = {
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": api_key,
        }

        total_matches_processed = 0
        total_goals_created = 0

        for current_date in distinct_dates:
            matches_qs = base_qs.filter(date__date=current_date)

            params = {
                "league": api_league_id,
                "season": season.year,
                "from": current_date.isoformat(),
                "to": current_date.isoformat(),
            }

            try:
                response = requests.get(
                    "https://v3.football.api-sports.io/fixtures",
                    headers=headers,
                    params=params,
                    timeout=15,
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao buscar fixtures em {current_date}: {e}"))
                current_date += timedelta(days=1)
                continue

            if response.status_code != 200:
                text = response.text[:300]
                self.stdout.write(
                    self.style.ERROR(
                        f"API-Football retornou {response.status_code} ao buscar fixtures em {current_date}: {text}"
                    )
                )
                current_date += timedelta(days=1)
                continue

            data = response.json()
            
            # Check for API errors (e.g. plan limits)
            errors = data.get("errors")
            if errors:
                self.stdout.write(self.style.ERROR(f"API Error on {current_date}: {errors}"))
                if isinstance(errors, dict) and "plan" in errors:
                    self.stdout.write(self.style.ERROR("Stopping import due to API plan limitation (2026 season not available on free plan)."))
                    break

            fixtures = data.get("response", [])
            # self.stdout.write(f"DEBUG: Date {current_date} - Found {len(fixtures)} fixtures in API")

            api_fixtures_map = {}
            for fx in fixtures:
                teams_data = fx.get("teams") or {}
                home_info = teams_data.get("home") or {}
                away_info = teams_data.get("away") or {}
                home_name_api = (home_info.get("name") or "").strip()
                away_name_api = (away_info.get("name") or "").strip()
                if not home_name_api or not away_name_api:
                    continue

                key = (self._normalize_name(home_name_api), self._normalize_name(away_name_api))
                api_fixtures_map[key] = fx

            for match in matches_qs:
                total_matches_processed += 1

                match_key = (
                    self._normalize_name(match.home_team.name),
                    self._normalize_name(match.away_team.name),
                )
                fx = api_fixtures_map.get(match_key)
                if not fx:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Fixture não encontrado na API para {match.home_team.name} x {match.away_team.name} em {current_date}"
                        )
                    )
                    continue

                fixture_info = fx.get("fixture") or {}
                fixture_id = fixture_info.get("id")
                if not fixture_id:
                    continue

                Goal.objects.filter(match=match).delete()

                events_params = {"fixture": fixture_id}
                try:
                    ev_response = requests.get(
                        "https://v3.football.api-sports.io/fixtures/events",
                        headers=headers,
                        params=events_params,
                        timeout=15,
                    )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Erro ao buscar eventos para fixture {fixture_id}: {e}"))
                    continue

                if ev_response.status_code != 200:
                    text = ev_response.text[:300]
                    self.stdout.write(
                        self.style.ERROR(
                            f"API-Football retornou {ev_response.status_code} ao buscar eventos do fixture {fixture_id}: {text}"
                        )
                    )
                    continue

                ev_data = ev_response.json()
                events = ev_data.get("response", [])

                for ev in events:
                    if ev.get("type") != "Goal":
                        continue

                    time_data = ev.get("time") or {}
                    minute = time_data.get("elapsed") or 0
                    extra = time_data.get("extra") or 0
                    minute_total = minute + (extra or 0)

                    team_data = ev.get("team") or {}
                    team_name_api = (team_data.get("name") or "").strip()
                    player_data = ev.get("player") or {}
                    player_name = player_data.get("name") or "Unknown"
                    detail = (ev.get("detail") or "").lower()

                    is_penalty = "penalty" in detail
                    is_own_goal = "own goal" in detail

                    team_obj = self._resolve_team(team_name_api, match)
                    if not team_obj:
                        continue

                    Goal.objects.create(
                        match=match,
                        team=team_obj,
                        player_name=player_name,
                        minute=minute_total,
                        is_own_goal=is_own_goal,
                        is_penalty=is_penalty,
                    )
                    total_goals_created += 1

            current_date += timedelta(days=1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Processo concluído: {total_matches_processed} partidas processadas, {total_goals_created} gols importados."
            )
        )

    def _normalize_name(self, name):
        return "".join(c for c in name.lower() if c.isalnum())

    def _resolve_team(self, api_team_name, match):
        norm_api = self._normalize_name(api_team_name)
        home_norm = self._normalize_name(match.home_team.name)
        away_norm = self._normalize_name(match.away_team.name)

        if norm_api == home_norm:
            return match.home_team
        if norm_api == away_norm:
            return match.away_team

        candidates = Team.objects.filter(league=match.league)
        for t in candidates:
            if self._normalize_name(t.name) == norm_api:
                return t

        return None
