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
            "--country",
            type=str,
            default=None,
            help="País da liga (opcional, para desambiguação)",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirma a operação de limpeza (obrigatório para executar)",
        )

    def handle(self, *args, **options):
        league_name = options["league_name"]
        country = options["country"]
        confirm = options.get("confirm", False)

        if not confirm:
            self.stdout.write(
                self.style.ERROR(
                    "ATENÇÃO: Este comando irá DELETAR todos os dados da liga!"
                )
            )
            cmd = f'python manage.py clear_league_data --league_name "{league_name}"'
            if country:
                cmd += f' --country "{country}"'
            cmd += ' --confirm'
            
            self.stdout.write(
                self.style.WARNING(
                    f"Para confirmar, execute: {cmd}"
                )
            )
            return

        try:
            leagues = League.objects.filter(name=league_name)
            if country:
                leagues = leagues.filter(country=country)
            
            if not leagues.exists():
                self.stdout.write(self.style.ERROR(f"Liga '{league_name}' (País: {country}) não encontrada"))
                return
            
            if leagues.count() > 1:
                self.stdout.write(self.style.WARNING(f"Encontradas {leagues.count()} ligas com nome '{league_name}':"))
                for l in leagues:
                     self.stdout.write(self.style.WARNING(f" - ID: {l.id} | País: {l.country}"))
                self.stdout.write(self.style.ERROR("Por favor, especifique o país com --country para desambiguar."))
                return

            league = leagues.first()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao buscar liga: {e}"))
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
