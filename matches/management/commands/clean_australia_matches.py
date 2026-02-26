from django.core.management.base import BaseCommand
from matches.models import League, Match, Season

class Command(BaseCommand):
    help = 'Limpa jogos da Australia da temporada atual antes de rodar o scraper para evitar duplicatas'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando limpeza de jogos da Austrália...')
        
        try:
            league = League.objects.get(name="A League", country="Australia")
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR('Liga "A League" (Australia) não encontrada!'))
            return

        # O scraper usa season 2026 (fim da temporada 25/26)
        try:
            season = Season.objects.get(year=2026)
            count, _ = Match.objects.filter(league=league, season=season).delete()
            self.stdout.write(self.style.SUCCESS(f'✅ Removidos {count} jogos da temporada 2026 (Austrália).'))
        except Season.DoesNotExist:
            self.stdout.write(self.style.WARNING('Season 2026 não existe. Nada removido.'))

        # Opcional: Limpar também season 2025 caso tenha sido criada erroneamente
        try:
            season25 = Season.objects.get(year=2025)
            count25, _ = Match.objects.filter(league=league, season=season25).delete()
            if count25 > 0:
                self.stdout.write(self.style.SUCCESS(f'✅ Removidos {count25} jogos da temporada 2025 (Austrália) para garantir limpeza.'))
        except Season.DoesNotExist:
            pass
            
        self.stdout.write(self.style.SUCCESS('Limpeza concluída! Agora pode rodar o scraper.'))
