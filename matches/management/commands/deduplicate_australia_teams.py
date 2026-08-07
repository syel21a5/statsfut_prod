
from django.core.management.base import BaseCommand
from matches.models import Team, League, Match

class Command(BaseCommand):
    help = 'Merge duplicate Australia teams (Scraper vs API)'

    def handle(self, *args, **options):
        try:
            league = League.objects.get(name="A League", country="Australia")
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR("League 'A League' (Australia) not found."))
            return

        # Map: "Bad Name" (Scraper) -> "Good Name" (API)
        # Based on observed duplicates
        duplicates = {
            "Adelaide Utd": "Adelaide United",
            "WS Wanderers": "Western Sydney Wanderers",
            "Melbourne V.": "Melbourne Victory",
            "Auckland": "Auckland FC",
            "Wellington": "Wellington Phoenix FC",
            "Central Coast": "Central Coast Mariners",
            "Newcastle Jets": "Newcastle Jets FC",
            # Add others if found later
            "Perth Glory FC": "Perth Glory", # Just in case
            "Macarthur": "Macarthur FC",     # Just in case
            "Sydney": "Sydney FC",           # Just in case
            "Brisbane": "Brisbane Roar",     # Just in case
            "Melbourne C.": "Melbourne City",# Just in case
        }

        self.stdout.write(f"Checking for duplicates in {league}...")

        all_teams = list(Team.objects.filter(league=league).values_list('name', flat=True))
        self.stdout.write(f"All teams in DB: {all_teams}")

        for bad_name, good_name in duplicates.items():
            bad_team = Team.objects.filter(name__iexact=bad_name, league=league).first()
            good_team = Team.objects.filter(name__iexact=good_name, league=league).first()
            
            self.stdout.write(f"Checking '{bad_name}' -> '{good_name}' | Found bad: {bad_team}, Found good: {good_team}")

            if bad_team and good_team:
                self.stdout.write(f"Merging '{bad_team.name}' -> '{good_team.name}'...")
                
                # Update matches
                matches_home = Match.objects.filter(home_team=bad_team)
                updated_home = matches_home.update(home_team=good_team)
                
                matches_away = Match.objects.filter(away_team=bad_team)
                updated_away = matches_away.update(away_team=good_team)
                
                self.stdout.write(f"  - Updated {updated_home} home matches, {updated_away} away matches.")
                
                # Delete bad team
                bad_team.delete()
                self.stdout.write(self.style.SUCCESS(f"  - Deleted '{bad_name}'"))
            
            elif bad_team and not good_team:
                # Rename bad team to good name if good team doesn't exist
                self.stdout.write(f"Renaming '{bad_team.name}' -> '{good_name}' (Target didn't exist)...")
                bad_team.name = good_name
                bad_team.save()
            
            else:
                # No bad team found, nothing to do
                pass

        self.stdout.write(self.style.SUCCESS("Deduplication complete."))
