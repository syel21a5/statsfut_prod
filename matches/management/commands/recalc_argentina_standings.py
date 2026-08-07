from django.core.management.base import BaseCommand
from django.core.management import call_command

from matches.models import League, Season


class Command(BaseCommand):
    help = "Recalcula standings da Liga Profesional (Argentina) para todas as temporadas com jogos"

    def handle(self, *args, **options):
        league = League.objects.filter(name="Liga Profesional", country="Argentina").first()
        if not league:
            self.stdout.write("Liga Profesional (Argentina) não encontrada")
            return

        seasons = (
            Season.objects.filter(matches__league=league)
            .distinct()
            .order_by("year")
        )
        if not seasons.exists():
            self.stdout.write("Nenhuma temporada com jogos encontrada para Liga Profesional")
            return

        for season in seasons:
            self.stdout.write(f"Recalculando standings para {league.name} {season.year}...")
            call_command(
                "recalculate_standings",
                league_name=league.name,
                country=league.country,
                season_year=season.year,
            )

        self.stdout.write(self.style.SUCCESS("Standings da Liga Profesional recalculados."))

