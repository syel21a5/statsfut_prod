from django.core.management.base import BaseCommand
from django.db import transaction
from matches.models import League, Team, Match
from matches.utils import TEAM_NAME_MAPPINGS


class Command(BaseCommand):
    help = "Deduplica times da Pro League (Bélgica) usando TEAM_NAME_MAPPINGS"

    def handle(self, *args, **options):
        league = League.objects.filter(name="Pro League", country="Belgica").first()

        if not league:
            self.stdout.write(self.style.ERROR("Liga Pro League (Belgica) não encontrada."))
            return

        self.stdout.write(f"Iniciando deduplicação para a liga: {league.name} - {league.country} (ID: {league.id})")

        mappings = TEAM_NAME_MAPPINGS

        with transaction.atomic():
            all_teams = Team.objects.filter(league=league)

            for team in all_teams:
                original_name = team.name
                clean_name = original_name.strip()

                if clean_name in mappings:
                    good_name = mappings[clean_name]

                    if clean_name == good_name:
                        continue

                    good_team = Team.objects.filter(name=good_name, league=league).first()

                    if good_team:
                        if good_team.id == team.id:
                            continue

                        self.stdout.write(
                            f"Mesclando '{original_name}' (ID: {team.id}) -> '{good_team.name}' (ID: {good_team.id})"
                        )

                        updated_home = Match.objects.filter(home_team=team).update(home_team=good_team)
                        updated_away = Match.objects.filter(away_team=team).update(away_team=good_team)

                        self.stdout.write(
                            f"  - Jogos movidos: {updated_home} (Casa) + {updated_away} (Fora)"
                        )

                        team.delete()
                    else:
                        self.stdout.write(
                            f"Renomeando '{original_name}' (ID: {team.id}) -> '{good_name}'"
                        )
                        team.name = good_name
                        team.save()

        self.stdout.write(self.style.SUCCESS("Deduplicação concluída para Pro League (Bélgica)."))

