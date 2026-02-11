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
            "Manchester United": "Manchester Utd",
            "Manchester United FC": "Manchester Utd",
            "Manchester City FC": "Manchester City",
            "Newcastle": "Newcastle Utd",
            "Newcastle United": "Newcastle Utd",
            "Newcastle United FC": "Newcastle Utd",
            "Nott'm Forest": "Nottm Forest",
            "Nottingham Forest": "Nottm Forest",
            "Nottingham Forest FC": "Nottm Forest",
            "West Ham": "West Ham Utd",
            "West Ham United": "West Ham Utd",
            "West Ham United FC": "West Ham Utd",  # Match API usage
            "Leeds": "Leeds Utd",
            "Leeds United": "Leeds Utd",
            "Leeds United FC": "Leeds Utd",
            "Sunderland AFC": "Sunderland",
            "Leicester City": "Leicester",
            "Leicester City FC": "Leicester",
            "Luton Town": "Luton",
            "Luton Town FC": "Luton",
            "Ipswich Town": "Ipswich",
            "Ipswich Town FC": "Ipswich",
            "Tottenham Hotspur": "Tottenham",
            "Tottenham Hotspur FC": "Tottenham",
            "Spurs": "Tottenham",
            "Wolverhampton Wanderers": "Wolverhampton",
            "Wolverhampton Wanderers FC": "Wolverhampton",
            "Brighton & Hove Albion": "Brighton",
            "Brighton & Hove Albion FC": "Brighton",
            "AFC Bournemouth": "Bournemouth",
            "Sheffield United": "Sheffield Utd",
            "Sheffield United FC": "Sheffield Utd",
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
