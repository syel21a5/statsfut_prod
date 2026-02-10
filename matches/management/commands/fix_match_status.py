from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import Match

class Command(BaseCommand):
    help = "Corrige status de jogos que têm placar mas não estão como 'Finished'"

    def handle(self, *args, **options):
        # Jogos passados, com placar, mas status != Finished
        matches = Match.objects.filter(
            date__lt=timezone.now(),
            home_score__isnull=False,
            away_score__isnull=False
        ).exclude(status="Finished")

        count = matches.count()
        self.stdout.write(f"Encontrados {count} jogos com status incorreto.")

        for match in matches:
            old_status = match.status
            match.status = "Finished"
            match.save()
            self.stdout.write(f"Corrigido: {match} ({old_status} -> Finished)")

        self.stdout.write(self.style.SUCCESS(f"Total corrigidos: {count}"))
