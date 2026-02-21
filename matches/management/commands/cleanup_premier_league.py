from django.core.management.base import BaseCommand
from django.db.models import Q

from matches.models import Match, League, Team, LeagueStanding, Season
from matches.team_validation import is_team_valid_for_league


class Command(BaseCommand):
    help = "Remove times e jogos que não pertencem à Premier League (limpeza de lixo de APIs)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Executar de fato a exclusão. Sem este flag é apenas DRY-RUN",
        )
        parser.add_argument(
            "--season_year",
            type=int,
            help="Ano da temporada para limitar a limpeza (ex: 2026). Se omitido, limpa todas as temporadas",
        )

    def handle(self, *args, **options):
        execute = options["execute"]
        season_year = options.get("season_year")

        if not execute:
            self.stdout.write(
                self.style.WARNING("DRY RUN - nada será deletado. Use --execute para aplicar as mudanças.")
            )

        league = (
            League.objects.filter(name="Premier League", country="Inglaterra").first()
            or League.objects.filter(name="Premier League").first()
        )
        if not league:
            self.stdout.write(self.style.ERROR("Liga 'Premier League' não encontrada"))
            return

        self.stdout.write(f"Liga: {league.name} ({league.country}) [ID: {league.id}]")

        season = None
        if season_year:
            season = Season.objects.filter(year=season_year).first()
            if not season:
                self.stdout.write(self.style.ERROR(f"Temporada {season_year} não encontrada"))
                return
            self.stdout.write(f"Limitando limpeza à temporada {season.year}")

        all_teams = Team.objects.filter(league=league)

        teams_to_keep = []
        for team in all_teams:
            if is_team_valid_for_league(team.name, "Premier League"):
                teams_to_keep.append(team)

        teams_to_delete = all_teams.exclude(id__in=[t.id for t in teams_to_keep])

        self.stdout.write(self.style.SUCCESS(f"Times na liga: {all_teams.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Times válidos para manter: {len(teams_to_keep)}"))
        self.stdout.write(self.style.WARNING(f"Times candidatos à remoção: {teams_to_delete.count()}"))

        for t in teams_to_delete[:50]:
            self.stdout.write(f"  ✗ {t.name}")
        if teams_to_delete.count() > 50:
            self.stdout.write(f"  ... e mais {teams_to_delete.count() - 50} times")

        if not teams_to_delete.exists():
            self.stdout.write(self.style.SUCCESS("Nenhum time inválido encontrado para remover."))
            return

        matches_qs = Match.objects.filter(
            league=league
        ).filter(Q(home_team__in=teams_to_delete) | Q(away_team__in=teams_to_delete))

        standings_qs = LeagueStanding.objects.filter(league=league, team__in=teams_to_delete)

        if season:
            matches_qs = matches_qs.filter(season=season)
            standings_qs = standings_qs.filter(season=season)

        self.stdout.write(f"Jogos a apagar: {matches_qs.count()}")
        self.stdout.write(f"Linhas de classificação a apagar: {standings_qs.count()}")

        if not execute:
            self.stdout.write(
                self.style.WARNING("DRY RUN finalizado. Nenhum dado foi apagado. Rode novamente com --execute para aplicar.")
            )
            return

        deleted_matches = matches_qs.delete()
        self.stdout.write(f"✓ Jogos deletados: {deleted_matches[0]}")

        deleted_standings = standings_qs.delete()
        self.stdout.write(f"✓ Classificações deletadas: {deleted_standings[0]}")

        remaining_matches = Match.objects.filter(
            league=league
        ).filter(Q(home_team__in=teams_to_delete) | Q(away_team__in=teams_to_delete))

        if remaining_matches.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Ainda existem jogos ligados a times inválidos ({remaining_matches.count()}). "
                    "Esses times não serão removidos para evitar erro de integridade."
                )
            )
        else:
            deleted_teams = teams_to_delete.delete()
            self.stdout.write(f"✓ Times deletados: {deleted_teams[0]}")

        self.stdout.write(self.style.SUCCESS("Limpeza da Premier League concluída."))

