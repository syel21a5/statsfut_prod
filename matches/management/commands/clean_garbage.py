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
        bad_names = [
            "MATCHES","FAV","AT","BE","Home","Away","Team","Averages","Percentages",
            "Copyright","Privacy","Defence","Offence","Form","Segment","Apr","Feb",
            "Jan","Mar","Points","Played","Goals","From","To","0%","1%","2%","3%","4%","5%"
        ]
        for name in bad_names:
            count = Match.objects.filter(home_team__name__icontains=name).delete()[0]
            if count:
                self.stdout.write(f"Deleted {count} matches with home team containing '{name}'")
            count = Match.objects.filter(away_team__name__icontains=name).delete()[0]
            if count:
                self.stdout.write(f"Deleted {count} matches with away team containing '{name}'")
        
        # Remove orphan teams that have no matches and look like garbage
        from matches.models import Team
        garbage_tokens = ["averages","percentages","copyright","privacy","defence","offence","segment"]
        to_delete = Team.objects.filter(matches__isnull=True)
        deleted = 0
        for t in to_delete:
            n = (t.name or "").lower()
            if any(tok in n for tok in garbage_tokens) or any(ch.isdigit() for ch in n) or '%' in n:
                t.delete()
                deleted += 1
        if deleted:
            self.stdout.write(f"Deleted {deleted} orphan garbage teams")
