from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import Match, LeagueStanding, Team, League

class Command(BaseCommand):
    help = "LIMPEZA TOTAL: Apaga jogos e tabelas para reimportar do zero e corrigir duplicatas."

    def handle(self, *args, **options):
        if input("Tem certeza que deseja APAGAR TODOS OS JOGOS e recriar o banco? (y/N): ").lower() != 'y':
            self.stdout.write(self.style.WARNING("Operação cancelada."))
            return

        self.stdout.write(self.style.WARNING("APAGANDO DADOS ANTIGOS..."))
        
        # 1. Apagar Tabelas e Jogos (Ordem importa por causa de FK)
        LeagueStanding.objects.all().delete()
        Match.objects.all().delete()
        
        # Não apagamos Times (Team) para não perder referências, mas o normalize vai limpar duplicatas
        # Se quiser apagar times também: Team.objects.all().delete() (Cuidado com FKs de outros lugares)
        
        self.stdout.write(self.style.SUCCESS("Jogos e classificações removidos."))

        # 2. Reimportar do CSV (Fonte Confiável) - Histórico Longo
        # Vamos pegar de 2021 até 2026 para garantir histórico recente robusto
        self.stdout.write(self.style.MIGRATE_HEADING("Reimportando dados da Football-Data (2021-2026)..."))
        call_command('import_football_data', min_year=2021)
        
        # 3. Normalizar Nomes (Crucial para evitar duplicatas Wolves/Wolverhampton)
        self.stdout.write(self.style.MIGRATE_HEADING("Normalizando nomes de times..."))
        call_command('normalize_teams', league_name="Premier League")
        
        # 4. Corrigir Status dos Jogos (Garantir que jogos com placar sejam 'Finished')
        self.stdout.write(self.style.MIGRATE_HEADING("Corrigindo status dos jogos..."))
        call_command('fix_match_status')
        
        # 5. Recalcular Tabela
        self.stdout.write(self.style.MIGRATE_HEADING("Recalculando tabela de classificação..."))
        call_command('recalculate_standings', league_name="Premier League")
        
        # 6. Atualizar Próximos Jogos (Upcoming)
        # Importante para preencher a tabela de Matches no frontend
        self.stdout.write(self.style.MIGRATE_HEADING("Buscando próximos jogos na API..."))
        try:
            call_command('update_live_matches', mode='upcoming')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Aviso: Não foi possível buscar próximos jogos agora ({e}). O script automático tentará depois."))

        self.stdout.write(self.style.SUCCESS("RECONSTRUÇÃO CONCLUÍDA COM SUCESSO!"))
