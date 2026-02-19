from django.core.management.base import BaseCommand
from django.db.models import Count
from matches.models import Match, League

class Command(BaseCommand):
    help = "Remove partidas duplicadas da Liga Profesional (Argentina) e Primera Division"

    def handle(self, *args, **kwargs):
        leagues = League.objects.filter(country="Argentina")
        if not leagues.exists():
            self.stdout.write("Nenhuma liga da Argentina encontrada.")
            return

        total_deleted = 0
        for league in leagues:
            self.stdout.write(f"Verificando duplicatas na liga: {league.name} (ID: {league.id})...")
            
            # Use distinct fields to identify duplicates
            duplicates = (
                Match.objects.filter(league=league)
                .values('date', 'home_team', 'away_team')
                .annotate(count=Count('id'))
                .filter(count__gt=1)
            )

            count_dupes = duplicates.count()
            self.stdout.write(f"Encontrados {count_dupes} grupos de duplicatas.")

            for item in duplicates:
                matches = Match.objects.filter(
                    league=league,
                    date=item['date'],
                    home_team=item['home_team'],
                    away_team=item['away_team']
                ).order_by('-id')
                
                matches_list = list(matches)
                # Keep the one with the highest ID (latest created/updated)
                to_delete = matches_list[1:]
                
                for m in to_delete:
                    m.delete()
                    total_deleted += 1

        self.stdout.write(self.style.SUCCESS(f"Total de partidas duplicadas removidas: {total_deleted}"))
