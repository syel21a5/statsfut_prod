import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League

class Command(BaseCommand):
    help = "Importa automaticamente todos os payloads JSON históricos da Championship (Inglaterra)."

    def handle(self, *args, **options):
        base_dir = "historical_data/Inglaterra/Championship"
        
        if not os.path.exists(base_dir):
            self.stdout.write(self.style.ERROR(f"Diretório {base_dir} não encontrado!"))
            return

        league_name = 'Championship'
        country = 'Inglaterra'

        # Garante a criação da liga se não existir no banco
        league, created = League.objects.get_or_create(
            name=league_name,
            country=country,
            defaults={'division': 2, 'soccerstats_slug': 'championship'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Liga '{league_name}' ({country}) criada no banco de dados com sucesso!"))

        self.stdout.write(self.style.SUCCESS(f"Iniciando importação histórica para {league_name} ({country})"))

        for year in range(2020, 2026):
            filename = f"{base_dir}/{year}.json"
            if os.path.exists(filename):
                self.stdout.write(self.style.WARNING(f"\n>>> Importando ano {year}..."))
                try:
                    # Usamos league_name e country para ele criar a liga automaticamente se não existir
                    call_command('import_sofascore_payload', file=filename, league_name=league_name, country=country, season_year=year)
                    self.stdout.write(self.style.SUCCESS(f"-> Sucesso ao importar {year}.json"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"-> Erro ao importar {year}.json: {e}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Arquivo não encontrado: {filename}"))

        self.stdout.write(self.style.WARNING("\nRecalculando tabelas..."))
        for year in range(2020, 2026):
             call_command('recalculate_standings', league_name=league_name, country=country, season_year=year)

        self.stdout.write(self.style.SUCCESS(f"\n✅ Importação histórica da {league_name} concluída!"))
