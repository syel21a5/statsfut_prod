from django.core.management.base import BaseCommand
from matches.models import League, Team, Match
from django.db import transaction

class Command(BaseCommand):
    help = 'Clean up Brazil and Premier League duplicates from import'

    def handle(self, *args, **options):
        # Mappings of Duplicate -> Correct
        duplicates_map = {
            # Brazil
            "CA Mineiro": "Atletico-MG",
            "CA Paranaense": "Athletico-PR",
            "Chapecoense AF": "Chapecoense",
            "Clube do Remo": "Remo",
            "Coritiba FBC": "Coritiba",
            "Mirassol FC": "Mirassol",
            "RB Bragantino": "Bragantino",
            "Red Bull Bragantino": "Bragantino",
            "Cuiaba Esporte Clube": "Cuiaba",
            "EC Juventude": "Juventude",
            "EC Vitoria": "Vitoria",
            "EC Bahia": "Bahia",
            "Fortaleza EC": "Fortaleza",
            "Goias EC": "Goias",
            "Ceara SC": "Ceara",
            "America FC": "America-MG",
            "America MG": "America-MG",
            "Sport Club do Recife": "Sport Recife",
            "Avai FC": "Avai",
            "CR Vasco da Gama": "Vasco",
            "Botafogo FR": "Botafogo",
            "Fluminense FC": "Fluminense",
            "SC Corinthians Paulista": "Corinthians",
            "SE Palmeiras": "Palmeiras",
            "Sao Paulo FC": "Sao Paulo",
            "Santos FC": "Santos",
            "Gremio FBPA": "Gremio",
            "Cruzeiro EC": "Cruzeiro",
            "SC Internacional": "Internacional",
            "Juventude RS": "Juventude",
            "CSA": "CSA",
            "AC Goianiense": "Atletico-GO",
            "Atletico Goianiense": "Atletico-GO",
            "Criciuma EC": "Criciuma",
            
            # Premier League
            "Manchester United FC": "Manchester Utd",
            "Manchester City FC": "Manchester City",
            "West Ham United FC": "West Ham",
            "Newcastle United FC": "Newcastle",
            "Tottenham Hotspur FC": "Tottenham",
            "Wolverhampton Wanderers FC": "Wolves",
            "Leicester City FC": "Leicester",
            "Leeds United FC": "Leeds",
            "Brighton & Hove Albion FC": "Brighton",
            "Arsenal FC": "Arsenal",
            "Chelsea FC": "Chelsea",
            "Liverpool FC": "Liverpool",
            "Everton FC": "Everton",
            "Fulham FC": "Fulham",
            "Brentford FC": "Brentford",
            "Crystal Palace FC": "Crystal Palace",
            "Southampton FC": "Southampton",
            "Aston Villa FC": "Aston Villa",
            "Sheffield United FC": "Sheffield United",
            "Burnley FC": "Burnley",
            "Luton Town FC": "Luton",
            "Norwich City FC": "Norwich",
            "Watford FC": "Watford",
            "Nottingham Forest FC": "Nottm Forest",
            "Ipswich Town FC": "Ipswich Town",
            "Wolves": "Wolverhampton",
            "Man City": "Manchester City",
            "Man United": "Manchester Utd",
            "Man Utd": "Manchester Utd",
            "Newcastle": "Newcastle Utd",
            "Nott'm Forest": "Nottm Forest",
            "Nottingham": "Nottm Forest",
            "Nottingham Forest": "Nottm Forest",
            "West Ham": "West Ham Utd",
            "Leeds": "Leeds Utd",
            "Leeds United": "Leeds Utd",
            "Sunderland AFC": "Sunderland",
            "AFC Bournemouth": "Bournemouth",
            "Ipswich": "Ipswich Town",
            "Sheffield Utd": "Sheffield United",
            "Sheff Utd": "Sheffield United",
        }

        self.stdout.write("Starting duplicate cleanup...")

        with transaction.atomic():
            for dup_name, correct_name in duplicates_map.items():
                # Find all teams with this duplicate name
                dup_teams = Team.objects.filter(name=dup_name)
                
                if not dup_teams.exists():
                    continue

                for dup_team in dup_teams:
                    # Try to find the correct team in the same league
                    correct_team = Team.objects.filter(name=correct_name, league=dup_team.league).first()
                    
                    # If not found in same league, try finding by country if it's unique enough (risky, but okay for these specific names)
                    if not correct_team:
                         correct_team = Team.objects.filter(name=correct_name, league__country=dup_team.league.country).first()

                    if not correct_team:
                         # If correct team doesn't exist, rename the duplicate to correct name
                        self.stdout.write(self.style.WARNING(f"Correct team '{correct_name}' not found for '{dup_name}' (ID: {dup_team.id}). Renaming..."))
                        dup_team.name = correct_name
                        dup_team.save()
                        continue
                    
                    if dup_team.id == correct_team.id:
                        continue

                    self.stdout.write(f"Merging '{dup_name}' (ID: {dup_team.id}) into '{correct_name}' (ID: {correct_team.id})...")

                    # Move home matches
                    Match.objects.filter(home_team=dup_team).update(home_team=correct_team)
                    # Move away matches
                    Match.objects.filter(away_team=dup_team).update(away_team=correct_team)
                    
                    # Delete duplicate
                    dup_team.delete()
                    self.stdout.write(self.style.SUCCESS(f"Deleted duplicate '{dup_name}'"))

        self.stdout.write(self.style.SUCCESS("Cleanup finished."))
