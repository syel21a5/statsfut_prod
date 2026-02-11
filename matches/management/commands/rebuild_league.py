from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from matches.models import League, Match
import sys

class Command(BaseCommand):
    help = 'Limpa e reconstrói os dados de uma liga para a temporada atual'

    def add_arguments(self, parser):
        parser.add_argument('league_name', type=str, help='Nome da liga (ex: "Premier League")')
        parser.add_argument('--year', type=int, default=2026, help='Ano final da temporada (ex: 2026 para 25/26)')

    def handle(self, *args, **options):
        league_name = options['league_name']
        year = options['year']
        
        self.stdout.write(self.style.WARNING(f"ATENÇÃO: Iniciando reconstrução RADICAL para {league_name}, ano {year}..."))
        
        try:
            league = League.objects.get(name=league_name, country="Inglaterra")
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Liga '{league_name}' não encontrada."))
            return

        # 1. Deletar jogos da temporada
        # A temporada geralmente cobre parte do ano anterior e o ano atual
        # Vamos deletar jogos com data >= Agosto do ano anterior
        start_date = f"{year-1}-07-01"
        
        self.stdout.write(f"Buscando jogos de {league.name} a partir de {start_date} para exclusão...")
        matches = Match.objects.filter(league=league, date__gte=start_date)
        count = matches.count()
        
        if count > 0:
            self.stdout.write(f"Deletando {count} jogos...")
            matches.delete()
            self.stdout.write(self.style.SUCCESS("Jogos deletados."))
        else:
            self.stdout.write("Nenhum jogo encontrado para deletar.")

        # 2. Reimportar
        self.stdout.write(self.style.MIGRATE_HEADING("2. Baixando e importando dados novos..."))
        # Importante: min_year deve pegar a temporada correta. Se year=2026, min_year=2026 no import deve funcionar
        try:
            call_command('import_football_data', min_year=year)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro na importação: {e}"))
            # Não paramos, pois pode ter importado algo
        
        # 3. Normalizar times
        self.stdout.write(self.style.MIGRATE_HEADING("3. Normalizando times..."))
        call_command('normalize_teams', league_name=league_name)
        
        # 4. Remover duplicatas
        self.stdout.write(self.style.MIGRATE_HEADING("4. Verificando duplicatas residuais..."))
        call_command('remove_match_duplicates')
        
        # 5. Recalcular tabela
        self.stdout.write(self.style.MIGRATE_HEADING("5. Recalculando tabela..."))
        call_command('recalculate_standings', league_name=league_name)
        
        self.stdout.write(self.style.SUCCESS("--------------------------------------------------"))
        self.stdout.write(self.style.SUCCESS("RECONSTRUÇÃO CONCLUÍDA COM SUCESSO!"))
        self.stdout.write(self.style.SUCCESS("Verifique se a tabela agora mostra os jogos corretos."))
