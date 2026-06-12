from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "OBSOLETO"
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("⚠️ OBSOLETO: Use update_pro_results e update_pro_odds via API-Football PRO."))
