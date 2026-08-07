from django.core.management.base import BaseCommand
from matches.models import Match

class Command(BaseCommand):
    help = "Remove dados de lixo"

    def handle(self, *args, **options):
        # Remove matches with no date
        count = Match.objects.filter(date__isnull=True).delete()[0]
        self.stdout.write(f"Deleted {count} matches with no date")

        # Remove matches with bad team names (headers)
        # Match EXACT header tokens only to avoid deleting valid teams like "Santos" or "Atletico"
        exact_bad_tokens = [
            "MATCHES","FAV","HOME","AWAY","TEAM","AVERAGES","PERCENTAGES",
            "COPYRIGHT","PRIVACY","DEFENCE","OFFENCE","FORM","SEGMENT",
            "APR","FEB","JAN","MAR","POINTS","PLAYED","GOALS","FROM","TO",
            "0%","1%","2%","3%","4%","5%"
        ]
        import re
        token_regex = re.compile(r'^(' + "|".join(exact_bad_tokens) + r')$', re.IGNORECASE)
        
        # Delete where the entire team name equals a header token
        count = Match.objects.filter(home_team__name__iregex=token_regex.pattern).delete()[0]
        if count:
            self.stdout.write(f"Deleted {count} matches with exact-header home team")
        count = Match.objects.filter(away_team__name__iregex=token_regex.pattern).delete()[0]
        if count:
            self.stdout.write(f"Deleted {count} matches with exact-header away team")
        
        # Remove orphan teams that have no matches and look like garbage
        from matches.models import Team
        garbage_tokens = ["averages","percentages","copyright","privacy","defence","offence","segment"]
        # Teams with no matches (neither home nor away)
        from django.db.models import Q
        to_delete = Team.objects.filter(home_matches__isnull=True, away_matches__isnull=True)
        deleted = 0
        for t in to_delete:
            n = (t.name or "").lower()
            if any(tok in n for tok in garbage_tokens) or any(ch.isdigit() for ch in n) or '%' in n:
                t.delete()
                deleted += 1
        if deleted:
            self.stdout.write(f"Deleted {deleted} orphan garbage teams")
