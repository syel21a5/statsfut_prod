import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import Match, League, Season


class Command(BaseCommand):
    help = "Exporta todos os jogos do Brasileirão 2026 para um arquivo JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="brasileriao_2026_matches.json",
            help="Caminho do arquivo de saída JSON",
        )

    def handle(self, *args, **options):
        output_path = options["output"]

        try:
            league = League.objects.get(name="Brasileirão")
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR("Liga 'Brasileirão' não encontrada"))
            return

        season, _ = Season.objects.get_or_create(year=2026)

        qs = (
            Match.objects.filter(league=league, season=season)
            .select_related("home_team", "away_team")
            .order_by("date", "id")
        )

        data = []
        for m in qs:
            if m.date is not None and timezone.is_aware(m.date):
                date_str = m.date.isoformat()
            elif m.date is not None:
                date_str = timezone.make_aware(m.date, timezone.get_current_timezone()).isoformat()
            else:
                date_str = None

            data.append(
                {
                    "home_team": m.home_team.name,
                    "away_team": m.away_team.name,
                    "date": date_str,
                    "home_score": m.home_score,
                    "away_score": m.away_score,
                    "ht_home_score": m.ht_home_score,
                    "ht_away_score": m.ht_away_score,
                }
            )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"Exportados {len(data)} jogos para {output_path}"))

