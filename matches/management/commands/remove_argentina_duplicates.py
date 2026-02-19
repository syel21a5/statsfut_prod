from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import TruncDate
from matches.models import Match, League

class Command(BaseCommand):
    help = "Remove partidas duplicadas da Liga Profesional (Argentina) e Primera Division (ignorando horário)"

    def handle(self, *args, **kwargs):
        leagues = League.objects.filter(country="Argentina")
        if not leagues.exists():
            self.stdout.write("Nenhuma liga da Argentina encontrada.")
            return

        total_deleted = 0
        for league in leagues:
            self.stdout.write(f"Verificando duplicatas na liga: {league.name} (ID: {league.id})...")
            
            # Agrupa por (data_sem_hora, home_team, away_team)
            # Usamos TruncDate para ignorar a parte da hora (UTC vs Local etc)
            duplicates = (
                Match.objects.filter(league=league)
                .annotate(match_date=TruncDate('date'))
                .values('match_date', 'home_team', 'away_team')
                .annotate(count=Count('id'))
                .filter(count__gt=1)
            )

            count_dupes = duplicates.count()
            self.stdout.write(f"Encontrados {count_dupes} grupos de duplicatas (por data).")

            for item in duplicates:
                matches = Match.objects.filter(
                    league=league,
                    date__date=item['match_date'],
                    home_team=item['home_team'],
                    away_team=item['away_team']
                ).order_by('-id')
                
                matches_list = list(matches)
                # Mantém o mais recente (maior ID), remove os outros
                to_delete = matches_list[1:]
                
                for m in to_delete:
                    m.delete()
                    total_deleted += 1

        self.stdout.write(self.style.SUCCESS(f"Total de partidas duplicadas removidas: {total_deleted}"))
