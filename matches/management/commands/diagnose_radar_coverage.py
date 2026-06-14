from django.core.management.base import BaseCommand
from matches.models import Match, League
from django.db.models import Q

class Command(BaseCommand):
    help = 'Analisa quais ligas ativas não possuem estatísticas avançadas preenchidas.'

    def handle(self, *args, **options):
        leagues = League.objects.filter(is_active=True)
        finished_statuses = ['FT', 'Finished', 'AET', 'PEN', 'Match Finished']

        results = []

        self.stdout.write("Buscando dados no banco. Isso pode levar alguns segundos...")

        for league in leagues:
            matches = Match.objects.filter(league=league, status__in=finished_statuses)
            total_matches = matches.count()
            if total_matches < 5:
                continue
                
            missing_stats = matches.filter(
                Q(home_shots_on_target__isnull=True) | Q(home_shots_on_target=0),
                Q(home_corners__isnull=True) | Q(home_corners=0),
                Q(home_dangerous_attacks__isnull=True) | Q(home_dangerous_attacks=0)
            ).count()
            
            if missing_stats > 0:
                pct = (missing_stats / total_matches) * 100
                if pct > 75:  # Consideramos "sem dados" se mais de 75% dos jogos não tiverem stats
                    results.append({
                        'name': league.name,
                        'country': league.country,
                        'total': total_matches,
                        'missing': missing_stats,
                        'pct': pct
                    })

        results.sort(key=lambda x: x['total'], reverse=True)

        self.stdout.write(self.style.SUCCESS("\n=== LIGAS ATIVAS SEM COBERTURA AVANÇADA (BASIC COVERAGE) ==="))
        self.stdout.write("Estas ligas têm histórico de não fornecer Chutes/Escanteios/Ataques para a API:\n")
        
        for r in results:
            msg = f"- {r['country']} | {r['name']} ({r['pct']:.1f}% dos {r['total']} jogos analisados estavam sem dados)"
            if r['pct'] > 95:
                self.stdout.write(self.style.ERROR(msg))
            else:
                self.stdout.write(self.style.WARNING(msg))
                
        self.stdout.write(self.style.SUCCESS(f"\nTotal encontrado: {len(results)} ligas.\n"))
