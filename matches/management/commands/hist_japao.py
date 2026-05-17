import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League

class Command(BaseCommand):
    help = "Importa automaticamente todos os payloads JSON históricos do Japão (J1 League)."

    def handle(self, *args, **options):
        base_dir = "historical_data/Japan/J1League"
        
        if not os.path.exists(base_dir):
            self.stdout.write(self.style.ERROR(f"Diretório {base_dir} não encontrado!"))
            return

        league = League.objects.filter(name__icontains='J1 League', country__icontains='Japao').first()
        if not league:
            self.stdout.write(self.style.ERROR("Liga 'J1 League' (Japão) não encontrada no banco."))
            return

        self.stdout.write(self.style.SUCCESS(f"Iniciando importação histórica para {league.name} (ID: {league.id})"))

        for year in range(2020, 2027):
            filename = f"{base_dir}/{year}.json"
            if os.path.exists(filename):
                self.stdout.write(self.style.WARNING(f"\n>>> Importando ano {year}..."))
                try:
                    call_command('import_sofascore_payload', file=filename, league_id=league.id, season_year=year)
                    self.stdout.write(self.style.SUCCESS(f"-> Sucesso ao importar {year}.json"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"-> Erro ao importar {year}.json: {e}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Arquivo não encontrado: {filename}"))

        self.stdout.write(self.style.WARNING("\nRecalculando tabelas..."))
        for year in range(2020, 2027):
             call_command('recalculate_standings', league_name='J1 League', country='Japao', season_year=year)

        self.stdout.write(self.style.SUCCESS(f"\n✅ Importação histórica do Japão concluída!"))
