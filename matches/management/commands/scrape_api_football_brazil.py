import os
from datetime import datetime, timedelta

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import League, Season, Team, Match


class Command(BaseCommand):
    help = "Atualiza jogos do Brasileirão 2026 usando API-Football"

    def handle(self, *args, **options):
        api_key = os.getenv("API_FOOTBALL_BRASILEIRAO_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("API_FOOTBALL_BRASILEIRAO_KEY não configurada no .env"))
            return

        league = League.objects.filter(name="Brasileirão").first()
        if not league:
            league = League.objects.filter(name__icontains="Brasileir").first()
        if not league:
            self.stdout.write(self.style.ERROR("Liga 'Brasileirão' não encontrada no banco"))
            return

        # Define a temporada atual dinamicamente (ano atual)
        current_year = timezone.now().year
        season, _ = Season.objects.get_or_create(year=current_year)

        url = "https://v3.football.api-sports.io/fixtures"
        params = {"league": 71, "season": season.year}
        headers = {
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": api_key,
        }

        self.stdout.write(self.style.SUCCESS(f"Buscando jogos do Brasileirão {season.year} na API-Football..."))
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao chamar API-Football: {e}"))
            return

        if response.status_code != 200:
            text = response.text[:300]
            self.stdout.write(self.style.ERROR(f"API-Football retornou {response.status_code}: {text}"))
            return

        data = response.json()
        fixtures = data.get("response", [])
        self.stdout.write(f"Total de jogos retornados: {len(fixtures)}")

        created = 0
        updated = 0
        skipped = 0

        for fx in fixtures:
            league_data = fx.get("league") or {}
            if int(league_data.get("id", 0)) != 71:
                continue
            if int(league_data.get("season", season.year)) != season.year:
                continue

            teams_data = fx.get("teams") or {}
            home_info = teams_data.get("home") or {}
            away_info = teams_data.get("away") or {}
            home_name_api = home_info.get("name")
            away_name_api = away_info.get("name")

            if not home_name_api or not away_name_api:
                skipped += 1
                continue

            home_team = self.resolve_team(home_name_api, league)
            away_team = self.resolve_team(away_name_api, league)
            if not home_team or not away_team:
                skipped += 1
                continue

            fixture_info = fx.get("fixture") or {}
            date_str = fixture_info.get("date")
            status_info = fixture_info.get("status") or {}
            status_short = status_info.get("short") or ""
            elapsed = status_info.get("elapsed")

            match_date = None
            if date_str:
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone.utc)
                    # Ajuste de -3 horas para alinhar com o horário do SoccerStats (UTC-3)
                    dt = dt - timedelta(hours=3)
                    match_date = dt
                except Exception:
                    match_date = None

            goals = fx.get("goals") or {}
            score = fx.get("score") or {}
            ht = score.get("halftime") or {}

            status = "Scheduled"
            finished_status = {"FT", "AET", "PEN"}
            inplay_status = {"1H", "HT", "2H", "ET", "P", "BT"}
            cancelled_status = {"PST", "CANC", "ABD", "AWD", "WO"}

            if status_short in finished_status:
                status = "Finished"
            elif status_short in inplay_status:
                status = "InPlay"
            elif status_short in cancelled_status:
                status = "Cancelled"

            defaults = {
                "date": match_date,
                "status": status,
                "home_score": goals.get("home"),
                "away_score": goals.get("away"),
                "ht_home_score": ht.get("home"),
                "ht_away_score": ht.get("away"),
                "round_name": league_data.get("round"),
                "elapsed_time": elapsed,
            }

            match = (
                Match.objects.filter(
                    league=league,
                    season=season,
                    home_team=home_team,
                    away_team=away_team,
                    date__date=match_date.date() if match_date else None,
                ).first()
                if match_date
                else None
            )

            if match:
                changed = False
                for field, value in defaults.items():
                    if getattr(match, field) != value:
                        setattr(match, field, value)
                        changed = True
                if changed:
                    match.save()
                    updated += 1
            else:
                match = Match.objects.create(
                    league=league,
                    season=season,
                    home_team=home_team,
                    away_team=away_team,
                    **defaults,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Criados: {created}, atualizados: {updated}, ignorados: {skipped}"))

    def resolve_team(self, name, league):
        # Tenta busca exata primeiro
        direct = Team.objects.filter(name__iexact=name, league=league).first()
        if direct:
            return direct

        # Mapeamento API-Football -> Nomes Canônicos do Banco
        # Deve estar alinhado com import_football_data.py
        mapping = {
            "SE Palmeiras": "Palmeiras",
            "CR Flamengo": "Flamengo",
            "Botafogo FR": "Botafogo",
            "São Paulo FC": "Sao Paulo",
            "Sao Paulo": "Sao Paulo",
            "Grêmio FBPA": "Gremio",
            "Gremio": "Gremio",
            "Clube Atlético Mineiro": "Atletico-MG",
            "Atlético Mineiro": "Atletico-MG",
            "Club Athletico Paranaense": "Athletico-PR",
            "Athletico Paranaense": "Athletico-PR",
            "Fluminense FC": "Fluminense",
            "Cuiabá EC": "Cuiaba",
            "Cuiaba": "Cuiaba",
            "SC Corinthians Paulista": "Corinthians",
            "Corinthians": "Corinthians",
            "Cruzeiro EC": "Cruzeiro",
            "Cruzeiro": "Cruzeiro",
            "SC Internacional": "Internacional",
            "Internacional": "Internacional",
            "Fortaleza EC": "Fortaleza",
            "Fortaleza": "Fortaleza",
            "EC Bahia": "Bahia",
            "Bahia": "Bahia",
            "CR Vasco da Gama": "Vasco",
            "Vasco da Gama": "Vasco",
            "EC Juventude": "Juventude",
            "Juventude": "Juventude",
            "AC Goianiense": "Atletico-GO",
            "Atlético Goianiense": "Atletico-GO",
            "Criciúma EC": "Criciuma",
            "Criciuma": "Criciuma",
            "EC Vitória": "Vitoria",
            "Vitoria": "Vitoria",
            "Red Bull Bragantino": "Bragantino",
            "Bragantino": "Bragantino",
            "Santos FC": "Santos",
            "Santos": "Santos",
            "Chapecoense": "Chapecoense",
            "Associação Chapecoense de Futebol": "Chapecoense",
            "Sport Club do Recife": "Sport Recife",
            "Sport Recife": "Sport Recife",
            "Ceará SC": "Ceara",
            "Ceara": "Ceara",
            "Goiás EC": "Goias",
            "Goias": "Goias",
            "América FC": "America-MG",
            "America MG": "America-MG",
            "Avaí FC": "Avai",
            "Avai": "Avai",
            "Coritiba FC": "Coritiba",
            "Coritiba": "Coritiba",
            "Mirassol FC": "Mirassol",
            "Mirassol": "Mirassol",
            "Clube do Remo": "Remo",
            "Remo": "Remo",
            "Paysandu SC": "Paysandu",
            "Paysandu": "Paysandu",
            "Vila Nova FC": "Vila Nova",
            "Novorizontino": "Novorizontino",
            "Grêmio Novorizontino": "Novorizontino",
        }

        target_name = mapping.get(name, name)
        team = Team.objects.filter(name__iexact=target_name, league=league).first()
        if team:
            return team

        # Tentativa final: busca parcial (perigoso, mas útil como fallback)
        simplified = name.split(" ")[0]
        # Evita match em nomes muito comuns se não tiver certeza
        if len(simplified) > 3:
            return Team.objects.filter(name__icontains=simplified, league=league).first()
        
        return None

