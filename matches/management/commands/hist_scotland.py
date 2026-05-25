import os
import json
from django.core.management.base import BaseCommand  # type: ignore
from django.core.management import call_command  # type: ignore
from matches.models import League

class Command(BaseCommand):
    help = "Importa automaticamente todos os payloads JSON históricos de Escocia (Premiership)."

    def handle(self, *args, **options):
        base_dir = "historical_data/Escocia/Premiership"

        if not os.path.exists(base_dir):
            self.stdout.write(self.style.ERROR(f"Diretório {base_dir} não encontrado!"))  # type: ignore
            return

        league, created = League.objects.get_or_create(name='Premiership', country='Escocia')  # type: ignore
        if created:
            self.stdout.write(self.style.SUCCESS("Liga 'Premiership' (Escocia) criada no banco."))  # type: ignore

        self.stdout.write(self.style.SUCCESS(f"Iniciando importação histórica para {league.name} (ID: {league.id})"))  # type: ignore

        for year in range(2020, 2026):
            filename = f"{base_dir}/{year}.json"
            if os.path.exists(filename):
                self.stdout.write(self.style.WARNING(f"\n>>> Importando ano {year}..."))  # type: ignore
                try:
                    call_command('import_sofascore_payload', file=filename, league_id=league.id, season_year=year)
                    self.stdout.write(self.style.SUCCESS(f"-> Sucesso ao importar {year}.json"))  # type: ignore
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"-> Erro ao importar {year}.json: {e}"))  # type: ignore
            else:
                self.stdout.write(self.style.NOTICE(f"Arquivo não encontrado: {filename}"))  # type: ignore

        self.stdout.write(self.style.WARNING("\nRecalculando tabelas..."))  # type: ignore
        for year in range(2020, 2026):
             call_command('recalculate_standings', league_name='Premiership', country='Escocia', season_year=year)

        self.stdout.write(self.style.SUCCESS(f"\n✅ Importação histórica de Escocia concluída!"))  # type: ignore
