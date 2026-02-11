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
        self.stdout.write("Iniciando normalização...")
        league_name = options["league_name"]

        try:
            league = League.objects.get(name=league_name, country="Inglaterra")
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Liga '{league_name}' (Inglaterra) não encontrada"))
            return
        except League.MultipleObjectsReturned:
            league = League.objects.filter(name=league_name, country="Inglaterra").first()
            self.stdout.write(self.style.WARNING(f"Múltiplas ligas encontradas, usando a primeira: {league}"))

        mappings = {
            "Wolves": "Wolverhampton",
            "Man City": "Manchester City",
            "Man United": "Manchester Utd",
            "Manchester United": "Manchester Utd",
            "Newcastle": "Newcastle Utd",
            "Newcastle United": "Newcastle Utd",
            "Nott'm Forest": "Nottm Forest",
            "Nottingham Forest": "Nottm Forest",
            "West Ham": "West Ham Utd",
            "West Ham United": "West Ham Utd",
            "Leeds": "Leeds Utd",
            "Leeds United": "Leeds Utd",
            "Sunderland AFC": "Sunderland",
            "Nottingham Forest FC": "Nottm Forest",
            "Leicester City": "Leicester",
            "Luton Town": "Luton",
            "Ipswich Town": "Ipswich",
            # Mapeamentos adicionais para remover sufixo FC e unificar
            "Arsenal FC": "Arsenal",
            "Liverpool FC": "Liverpool",
            "Manchester United FC": "Manchester Utd",
            "Manchester City FC": "Manchester City",
            "Chelsea FC": "Chelsea",
            "Tottenham Hotspur FC": "Tottenham",
            "Tottenham Hotspur": "Tottenham",
            "Everton FC": "Everton",
            "Aston Villa FC": "Aston Villa",
            "Wolverhampton Wanderers FC": "Wolverhampton",
            "Wolverhampton Wanderers": "Wolverhampton",
            "Brighton & Hove Albion FC": "Brighton",
            "Brighton & Hove Albion": "Brighton",
            "Brentford FC": "Brentford",
            "Fulham FC": "Fulham",
            "Crystal Palace FC": "Crystal Palace",
            "Burnley FC": "Burnley",
            "Sheffield United FC": "Sheffield Utd",
            "Sheffield United": "Sheffield Utd",
            "Luton Town FC": "Luton",
            "Bournemouth AFC": "Bournemouth",
            "AFC Bournemouth": "Bournemouth",
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
