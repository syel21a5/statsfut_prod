from django.core.management.base import BaseCommand
from matches.models import League, Team, Match

class Command(BaseCommand):
    help = 'Clean Belgium Data'

    def handle(self, *args, **options):
        leagues = League.objects.filter(name__icontains="Pro League")
        self.stdout.write(f"Ligas encontradas: {leagues.count()}")
        for l in leagues:
            self.stdout.write(f" - {l.name} ({l.country}) ID: {l.id} Matches: {Match.objects.filter(league=l).count()}")
            
        league = League.objects.filter(name__icontains="Pro League", country="Belgica").first()
        if not league:
            self.stdout.write("Liga 'Belgica' não encontrada. Tentando 'Belgium'...")
            league = League.objects.filter(name__icontains="Pro League", country="Belgium").first()

        if not league:
            self.stdout.write("Liga não encontrada.")
            return

        self.stdout.write(f"Selecionada: {league.name} ({league.country}) ID: {league.id}")
        matches = Match.objects.filter(league=league)
        count_m = matches.count()
        self.stdout.write(f"Encontradas {count_m} partidas para deletar.")
        matches.delete()
        self.stdout.write(f"Deletando {count_m} partidas...")
        
        teams = Team.objects.filter(league=league)
        count_t = teams.count()
        teams.delete()
        self.stdout.write(f"Deletando {count_t} times...")
        
        self.stdout.write("Dados deletados com sucesso.")
