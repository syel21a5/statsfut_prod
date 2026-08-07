from django.core.management.base import BaseCommand
from matches.models import Match, League, Season, LeagueStanding

class Command(BaseCommand):
    help = 'WIPE OUT Austria matches for 2026 to fix duplication issues'

    def handle(self, *args, **options):
        self.stdout.write("INICIANDO LIMPEZA RADICAL DA ÁUSTRIA...")
        
        try:
            league = League.objects.filter(country="Austria").first()
            if not league:
                self.stdout.write(self.style.ERROR("Liga da Áustria não encontrada."))
                return

            season = Season.objects.get(year=2026)
            
            # 1. Apagar jogos
            matches = Match.objects.filter(league=league, season=season)
            count = matches.count()
            matches.delete()
            self.stdout.write(self.style.SUCCESS(f"✅ {count} partidas da Áustria 2026 foram APAGADAS."))
            
            # 2. Apagar tabela
            standings = LeagueStanding.objects.filter(league=league, season=season)
            st_count = standings.count()
            standings.delete()
            self.stdout.write(self.style.SUCCESS(f"✅ {st_count} registros de tabela foram APAGADOS."))
            
            self.stdout.write(self.style.SUCCESS("Agora a liga está vazia. Pode rodar o scraper para reimportar do zero."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro: {e}"))
