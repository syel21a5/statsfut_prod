from django.core.management.base import BaseCommand
from matches.utils_odds_api import fetch_upcoming_odds_api_belgium

class Command(BaseCommand):
    help = 'Update upcoming matches for Belgium Pro League via The Odds API'

    def handle(self, *args, **options):
        self.stdout.write("🇧🇪 Iniciando atualização de jogos futuros da Bélgica...")
        fetch_upcoming_odds_api_belgium()
        self.stdout.write("✅ Atualização concluída.")
