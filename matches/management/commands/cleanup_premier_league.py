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

        self.stdout.write(f"Total de jogos a apagar (em todas as temporadas): {matches_qs.count()}")
        self.stdout.write(f"Total de classificações a apagar (em todas as temporadas): {standings_qs.count()}")

        if season:
            self.stdout.write(
                f"-> Desses, {matches_qs.filter(season=season).count()} jogos são da temporada {season.year}"
            )
            self.stdout.write(
                f"-> Desses, {standings_qs.filter(season=season).count()} classificações são da temporada {season.year}"
            )

        if not execute:
            self.stdout.write(
                self.style.WARNING("DRY RUN finalizado. Nenhum dado foi apagado. Rode novamente com --execute para aplicar.")
            )
            return

        deleted_matches_count = deleted_matches[0] if isinstance(deleted_matches, tuple) else 0
        self.stdout.write(f"✓ Jogos deletados: {deleted_matches_count}")

        deleted_standings = standings_qs.delete()
        deleted_standings_count = deleted_standings[0] if isinstance(deleted_standings, tuple) else 0
        self.stdout.write(f"✓ Classificações deletadas: {deleted_standings_count}")

        # Força a exclusão dos times, agora que as dependências foram removidas
        try:
            deleted_teams = teams_to_delete.delete()
            deleted_teams_count = deleted_teams[0] if isinstance(deleted_teams, tuple) else 0
            self.stdout.write(f"✓ Times deletados: {deleted_teams_count}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao deletar times: {e}"))
            remaining_teams = Team.objects.filter(id__in=teams_to_delete.values_list('id', flat=True))
            self.stdout.write(self.style.WARNING(f"Times que não puderam ser removidos: {remaining_teams.count()}"))
            for team in remaining_teams[:10]:
                self.stdout.write(f"  - {team.name}")

        self.stdout.write(self.style.SUCCESS("Limpeza da Premier League concluída."))

