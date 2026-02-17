import os
import json
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone

from matches.models import League, Team, Match, Season, LeagueStanding
from matches.utils import normalize_team_name


class Command(BaseCommand):
    help = "Reseta completamente o Brasileirão 2026 usando o arquivo brasileirao_2026_matches.json"

    def handle(self, *args, **options):
        league = League.objects.filter(name="Brasileirão").first()
        if not league:
            league = League.objects.filter(name="Brasileirao").first()
        if not league:
            self.stdout.write(self.style.ERROR("Liga Brasileirão não encontrada."))
            return

        season, _ = Season.objects.get_or_create(year=2026)

        matches_qs = Match.objects.filter(league=league, season=season)
        matches_count = matches_qs.count()
        matches_qs.delete()

        standings_qs = LeagueStanding.objects.filter(league=league, season=season)
        standings_count = standings_qs.count()
        standings_qs.delete()

        self.stdout.write(f"Jogos apagados para 2026: {matches_count}")
        self.stdout.write(f"Classificações apagadas para 2026: {standings_count}")

        json_path = os.path.join(settings.BASE_DIR, "brasileirao_2026_matches.json")
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f"Arquivo não encontrado: {json_path}"))
            return

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        created_matches = 0
        for item in data:
            home_name = normalize_team_name(item.get("home_team"))
            away_name = normalize_team_name(item.get("away_team"))

            if not home_name or not away_name:
                continue

            home_team, _ = Team.objects.get_or_create(name=home_name, league=league)
            away_team, _ = Team.objects.get_or_create(name=away_name, league=league)

            date_str = item.get("date")
            if not date_str:
                continue

            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.utc)
            except Exception:
                continue

            home_score = item.get("home_score")
            away_score = item.get("away_score")
            ht_home_score = item.get("ht_home_score")
            ht_away_score = item.get("ht_away_score")

            status = "Scheduled"
            if home_score is not None and away_score is not None:
                status = "Finished"

            Match.objects.create(
                league=league,
                season=season,
                home_team=home_team,
                away_team=away_team,
                date=dt,
                status=status,
                home_score=home_score,
                away_score=away_score,
                ht_home_score=ht_home_score,
                ht_away_score=ht_away_score,
            )
            created_matches += 1

        self.stdout.write(self.style.SUCCESS(f"Jogos criados para 2026: {created_matches}"))

        call_command("recalculate_standings", league_name="Brasileirao", season_year=2026)
        self.stdout.write(self.style.SUCCESS("Tabela do Brasileirão 2026 recalculada."))
