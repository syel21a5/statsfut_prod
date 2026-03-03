from django.core.management.base import BaseCommand
from matches.models import Team, LeagueStanding, League, Season
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Force cleanup Australia table (remove bad Western United and recalculate)'

    def handle(self, *args, **options):
        # 1. Identificar o time ruim (Western United com poucos jogos/pontos errados)
        # O usuário mostrou ID 2091 com 2 pontos em 2 jogos.
        # Vamos remover especificamente esse ID se ele existir.
        
        target_id = 2091
        
        self.stdout.write(f"Iniciando limpeza da Austrália...")
        
        try:
            bad_team = Team.objects.get(id=target_id)
            self.stdout.write(f"Encontrado time para remover: {bad_team.name} (ID: {bad_team.id})")
            bad_team.delete()
            self.stdout.write(self.style.SUCCESS(f"Time ID {target_id} removido com sucesso!"))
        except Team.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"Time ID {target_id} não encontrado (já foi removido?)."))

        # 2. Limpar a tabela de classificação da A League 2026 para garantir
        try:
            league = League.objects.get(name="A League", country="Australia")
            season = Season.objects.get(year=2026)
            
            deleted_count, _ = LeagueStanding.objects.filter(league=league, season=season).delete()
            self.stdout.write(self.style.SUCCESS(f"Tabela limpa! {deleted_count} registros removidos."))
            
            # 3. Recalcular
            self.stdout.write("Recalculando tabela...")
            call_command('recalculate_standings', league_name="A League", season_year=2026)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao limpar/recalcular: {e}"))
