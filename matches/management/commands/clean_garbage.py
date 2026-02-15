from django.core.management.base import BaseCommand
from matches.models import Match

class Command(BaseCommand):
    help = "Remove dados de lixo"

    def handle(self, *args, **options):
        # Remove matches with no date
        count = Match.objects.filter(date__isnull=True).delete()[0]
        self.stdout.write(f"Deleted {count} matches with no date")

        # Remove matches with bad team names (headers)
        # Using icontains for broad matching of potential header artifacts
        bad_names = ["MATCHES", "FAV", "AT", "BE", "Home", "Away", "Team"]
        for name in bad_names:
            count = Match.objects.filter(home_team__name__icontains=name).delete()[0]
            if count:
                self.stdout.write(f"Deleted {count} matches with home team containing '{name}'")
            count = Match.objects.filter(away_team__name__icontains=name).delete()[0]
            if count:
                self.stdout.write(f"Deleted {count} matches with away team containing '{name}'")
