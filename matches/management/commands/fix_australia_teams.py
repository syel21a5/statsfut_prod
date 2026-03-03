from django.core.management.base import BaseCommand
from matches.models import Team, Match, League
from django.db.models import Q

class Command(BaseCommand):
    help = 'Fix Australia teams (Merge split teams)'

    def handle(self, *args, **options):
        try:
            league = League.objects.get(name="A League", country="Australia")
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR("League 'A League' (Australia) not found."))
            return

        # Map: "Wrong Name" -> "Correct Name"
        # We want to standardize on what matches utils_odds_api.py
        merges = {
            # Newcastle Jets -> Newcastle Jets FC
            "Newcastle Jets": "Newcastle Jets FC",
            
            # Wellington Phoenix -> Wellington Phoenix FC
            "Wellington Phoenix": "Wellington Phoenix FC",
            "Wellington": "Wellington Phoenix FC",
            
            # Western United FC -> Western United
            "Western United FC": "Western United",
            "Western Utd": "Western United",
            
            # Others just in case
            "Melbourne City FC": "Melbourne City",
            "Melbourne Victory FC": "Melbourne Victory",
            "Adelaide United FC": "Adelaide United",
            "Perth Glory FC": "Perth Glory",
            "Brisbane Roar FC": "Brisbane Roar",
            "Macarthur": "Macarthur FC",
            "Auckland": "Auckland FC",
            "Central Coast": "Central Coast Mariners",
        }

        self.stdout.write(f"Starting Australia Team Fix for {league}...")

        for wrong, correct in merges.items():
            self.merge_teams(league, wrong, correct)

        self.stdout.write(self.style.SUCCESS("Australia Fix Completed."))

    def merge_teams(self, league, wrong_name, correct_name):
        # Find correct team
        correct_team = Team.objects.filter(name__iexact=correct_name, league=league).first()
        if not correct_team:
            # If correct team doesn't exist, maybe we just rename the wrong one if it exists?
            wrong_team = Team.objects.filter(name__iexact=wrong_name, league=league).first()
            if wrong_team:
                self.stdout.write(f"Renaming '{wrong_team.name}' -> '{correct_name}' (Target didn't exist)")
                wrong_team.name = correct_name
                wrong_team.save()
            return

        # Find wrong team
        # Exclude the correct team itself
        wrong_teams = Team.objects.filter(name__iexact=wrong_name, league=league).exclude(id=correct_team.id)

        for wrong_team in wrong_teams:
            self.stdout.write(f"Merging '{wrong_team.name}' (ID: {wrong_team.id}) -> '{correct_team.name}' (ID: {correct_team.id})...")
            
            # Update Matches (Home)
            count_home = Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
            # Update Matches (Away)
            count_away = Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
            
            self.stdout.write(f"  - Moved {count_home} home matches and {count_away} away matches.")
            
            # Delete wrong team
            wrong_team.delete()
            self.stdout.write(f"  - Deleted '{wrong_team.name}'")
