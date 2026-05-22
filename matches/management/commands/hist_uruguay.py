import os
import json
from django.core.management.base import BaseCommand  # type: ignore
from django.core.management import call_command  # type: ignore
from matches.models import League

class Command(BaseCommand):
    help = "Importa automaticamente todos os payloads JSON históricos do Uruguai (Primera Division)."

    def handle(self, *args, **options):
        base_dir = "historical_data/Uruguay/PrimeraDivision"
        
        if not os.path.exists(base_dir):
            self.stdout.write(self.style.ERROR(f"Diretório {base_dir} não encontrado!"))  # type: ignore
            return

        # Busca a liga no banco de dados.
        league = League.objects.filter(name__icontains='Primera Division', country__icontains='Uruguai').first()  # type: ignore
        if not league:
            self.stdout.write(self.style.ERROR("Liga 'Primera Division' (Uruguai) não encontrada no banco."))  # type: ignore
            return

        self.stdout.write(self.style.SUCCESS(f"Iniciando importação histórica para {league.name} (ID: {league.id})"))  # type: ignore

        for year in range(2020, 2027):
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
        for year in range(2020, 2027):
             call_command('recalculate_standings', league_name='Primera Division', country='Uruguai', season_year=year)

        self.stdout.write(self.style.SUCCESS(f"\n✅ Importação histórica do Uruguai concluída!"))  # type: ignore
