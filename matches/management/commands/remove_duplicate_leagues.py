from django.core.management.base import BaseCommand
from django.db.models import Count
from matches.models import League, Team, Match

class Command(BaseCommand):
    help = 'Remove ligas duplicadas, mantendo a mais antiga e reassociando times/jogos'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando limpeza de ligas duplicadas...")

        # Encontra nomes de ligas duplicadas
        duplicates = League.objects.values('name').annotate(count=Count('id')).filter(count__gt=1)

        for entry in duplicates:
            name = entry['name']
            self.stdout.write(f"Processando duplicatas para: {name}")

            # Pega todas as ligas com esse nome, ordenadas por ID (a primeira é a mais antiga)
            leagues = list(League.objects.filter(name=name).order_by('id'))
            
            # A primeira é a "original" que vamos manter
            main_league = leagues[0]
            redundant_leagues = leagues[1:]

            self.stdout.write(f"  > Mantendo ID {main_league.id} ({main_league.country})")
            
            for redundant in redundant_leagues:
                self.stdout.write(f"  > Removendo ID {redundant.id} ({redundant.country})...")
                
                # Reassocia Times
                teams = Team.objects.filter(league=redundant)
                count_teams = teams.count()
                teams.update(league=main_league)
                if count_teams > 0:
                    self.stdout.write(f"    - {count_teams} times movidos.")

                # Reassocia Jogos (Matches)
                matches = Match.objects.filter(league=redundant)
                count_matches = matches.count()
                matches.update(league=main_league)
                if count_matches > 0:
                    self.stdout.write(f"    - {count_matches} jogos movidos.")
                
                # Deleta a liga redundante
                redundant.delete()
                self.stdout.write(f"    - Liga ID {redundant.id} deletada.")

        self.stdout.write(self.style.SUCCESS("Limpeza concluída!"))
