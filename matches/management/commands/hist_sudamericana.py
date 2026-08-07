import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League

class Command(BaseCommand):
    help = "Importa automaticamente todos os payloads JSON historicos da Copa Sul-Americana."

    def handle(self, *args, **options):
        base_dir = "historical_data/America do Sul/Copa Sul-Americana"
        
        if not os.path.exists(base_dir):
            self.stdout.write(self.style.ERROR(f"Diretorio {base_dir} nao encontrado!"))
            return

        league_name = 'Copa Sul-Americana'
        country = 'America do Sul'

        # Garante a criacao da liga se nao existir no banco
        league, created = League.objects.get_or_create(
            name=league_name,
            country=country,
            defaults={'division': 1}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Liga '{league_name}' ({country}) criada no banco de dados com sucesso!"))

        self.stdout.write(self.style.SUCCESS(f"Iniciando importacao historica para {league_name} ({country})"))

        for year in range(2020, 2027):
            filename = f"{base_dir}/{year}.json"
            if os.path.exists(filename):
                self.stdout.write(self.style.WARNING(f"\n>>> Importando ano {year}..."))
                try:
                    call_command('import_sofascore_payload', file=filename, league_name=league_name, country=country, season_year=year)
                    self.stdout.write(self.style.SUCCESS(f"-> Sucesso ao importar {year}.json"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"-> Erro ao importar {year}.json: {e}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Arquivo nao encontrado: {filename}"))

        self.stdout.write(self.style.WARNING("\nRecalculando tabelas..."))
        for year in range(2020, 2027):
             call_command('recalculate_standings', league_name=league_name, country=country, season_year=year)

        self.stdout.write(self.style.SUCCESS(f"\n✅ Importacao historica da {league_name} concluida!"))
