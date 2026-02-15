import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import Match, League, Season, Team


class Command(BaseCommand):
    help = "Importa jogos do Brasileirão 2026 a partir de um arquivo JSON exportado"

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            type=str,
            default="brasileriao_2026_matches.json",
            help="Caminho do arquivo JSON de entrada",
        )

    def handle(self, *args, **options):
        input_path = options["input"]

        try:
            league = League.objects.get(name="Brasileirão")
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR("Liga 'Brasileirão' não encontrada"))
            return

        season, _ = Season.objects.get_or_create(year=2026)

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Arquivo não encontrado: {input_path}"))
            return

        created = 0
        updated = 0
        skipped = 0

        tz = timezone.get_current_timezone()

        for item in data:
            home_name = item.get("home_team")
            away_name = item.get("away_team")
            date_str = item.get("date")

            if not home_name or not away_name or not date_str:
                skipped += 1
                continue

            try:
                home_team = Team.objects.get(name=home_name)
                away_team = Team.objects.get(name=away_name)
            except Team.DoesNotExist:
                skipped += 1
                continue

            try:
                dt = datetime.fromisoformat(date_str)
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, tz)
            except Exception:
                skipped += 1
                continue

            match, created_flag = Match.objects.get_or_create(
                league=league,
                season=season,
                home_team=home_team,
                away_team=away_team,
                date=dt,
            )

            match.home_score = item.get("home_score")
            match.away_score = item.get("away_score")
            match.ht_home_score = item.get("ht_home_score")
            match.ht_away_score = item.get("ht_away_score")
            match.save()

            if created_flag:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Importação concluída. Criados: {created}, atualizados: {updated}, ignorados: {skipped}"
            )
        )

