from django.core.management.base import BaseCommand
from django.db import transaction

from matches.models import League, Team, Match, LeagueStanding, Season


class Command(BaseCommand):
    help = "Limpa todos os dados de uma liga específica (times, jogos, classificação)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--league_name",
            type=str,
            default="Premier League",
            help="Nome da liga para limpar os dados",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirma a operação de limpeza (obrigatório para executar)",
        )

    def handle(self, *args, **options):
        league_name = options["league_name"]
        confirm = options.get("confirm", False)

        if not confirm:
            self.stdout.write(
                self.style.ERROR(
                    "ATENÇÃO: Este comando irá DELETAR todos os dados da liga!"
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    f"Para confirmar, execute: python manage.py clear_league_data --league_name \"{league_name}\" --confirm"
                )
            )
            return

        try:
            league = League.objects.get(name=league_name)
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Liga '{league_name}' não encontrada"))
            return

        self.stdout.write(
            self.style.WARNING(f"Iniciando limpeza de dados para: {league.name}")
        )

        with transaction.atomic():
            # 1. Delete standings
            standings_count = LeagueStanding.objects.filter(league=league).count()
            LeagueStanding.objects.filter(league=league).delete()
            self.stdout.write(f"✓ Classificações deletadas: {standings_count}")

            # 2. Delete matches
            matches_count = Match.objects.filter(league=league).count()
            Match.objects.filter(league=league).delete()
            self.stdout.write(f"✓ Jogos deletados: {matches_count}")

            # 3. Delete teams
            teams_count = Team.objects.filter(league=league).count()
            Team.objects.filter(league=league).delete()
            self.stdout.write(f"✓ Times deletados: {teams_count}")

            # 4. Optionally clean up orphaned seasons (seasons with no matches)
            orphaned_seasons = Season.objects.filter(matches__isnull=True).distinct()
            orphaned_count = orphaned_seasons.count()
            orphaned_seasons.delete()
            self.stdout.write(f"✓ Temporadas órfãs deletadas: {orphaned_count}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Limpeza concluída para {league.name}!\n"
                f"   - {standings_count} classificações\n"
                f"   - {matches_count} jogos\n"
                f"   - {teams_count} times\n"
                f"   - {orphaned_count} temporadas órfãs"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "\n⚠️  Agora você pode importar dados frescos com:\n"
                f"   python manage.py import_football_data --division E0 --min_year 2010"
            )
        )
