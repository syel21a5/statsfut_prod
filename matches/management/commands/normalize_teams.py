from django.core.management.base import BaseCommand

from matches.models import League, Team, Match, LeagueStanding


class Command(BaseCommand):
    help = "Normaliza nomes de times da liga, unificando apelidos em um único time"

    def add_arguments(self, parser):
        parser.add_argument(
            "--league_name",
            type=str,
            default="Premier League",
            help="Nome da liga para normalizar",
        )

    def handle(self, *args, **options):
        league_name = options["league_name"]

        try:
            league = League.objects.get(name=league_name)
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Liga '{league_name}' não encontrada"))
            return

        mappings = {
            "Wolves": "Wolverhampton",
            "Man City": "Manchester City",
            "Man United": "Manchester Utd",
            "Manchester United": "Manchester Utd",  # Added alias
            "Newcastle": "Newcastle Utd",
            "Newcastle United": "Newcastle Utd",    # Added alias
            "Nott'm Forest": "Nottm Forest",
            "Nottingham Forest": "Nottm Forest",    # Added alias
            "West Ham": "West Ham Utd",
            "West Ham United": "West Ham Utd",      # Added alias
            "Leeds": "Leeds Utd",
            "Leeds United": "Leeds Utd",            # Added alias
            "Sunderland AFC": "Sunderland",
            "Nottingham Forest FC": "Nottm Forest",
            "Leicester City": "Leicester",          # Standardizing
            "Luton Town": "Luton",
            "Ipswich Town": "Ipswich",
        }

        for alias_name, canonical_name in mappings.items():
            alias = Team.objects.filter(name=alias_name, league=league).first()
            canonical = Team.objects.filter(name=canonical_name, league=league).first()

            if not alias:
                continue

            if not canonical:
                alias.name = canonical_name
                alias.save(update_fields=["name"])
                continue

            Match.objects.filter(home_team=alias).update(home_team=canonical)
            Match.objects.filter(away_team=alias).update(away_team=canonical)

            LeagueStanding.objects.filter(team=alias).delete()

            alias.delete()

        self.stdout.write(self.style.SUCCESS("Normalização de times concluída"))
