import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League, Season

class Command(BaseCommand):
    help = "Importa o histórico da Dinamarca (Superliga) a partir dos arquivos JSON locais."

    def handle(self, *args, **options):
        # Configurações da liga
        league_name = "Superliga"
        country = "Dinamarca"
        base_dir = os.path.join("historical_data", "Denmark", "Superliga")

        if not os.path.exists(base_dir):
            self.stdout.write(self.style.ERROR(f"Diretório não encontrado: {base_dir}"))
            return

        # Garante que a liga exista
        league, created = League.objects.get_or_create(
            name=league_name,
            country=country,
            defaults={"division": 1}
        )

        # Arquivos esperados
        # 2021.json (Temporada 2020/21) -> year=2021
        # ...
        # 2026.json (Temporada 2025/26) -> year=2026

        files = sorted([f for f in os.listdir(base_dir) if f.endswith(".json") and f.replace(".json", "").isdigit()])

        for filename in files:
            year_str = filename.replace(".json", "")
            try:
                year = int(year_str)
            except ValueError:
                continue

            self.stdout.write(self.style.SUCCESS(f"\n>>> Importando {league_name} {year-1}/{year} ({filename})"))
            
            # Garante que a Season exista
            season, _ = Season.objects.get_or_create(year=year)

            file_path = os.path.join(base_dir, filename)
            
            # Chama o comando de importação nativo
            call_command(
                "import_sofascore_payload",
                file=file_path,
                league_name=league_name,
                country=country,
                season_year=year
            )

            # Recalcula standings para esta temporada
            self.stdout.write(f"Recalculando classificação para {year}...")
            call_command(
                "recalculate_standings",
                league_name=league_name,
                country=country,
                season_year=year
            )

        self.stdout.write(self.style.SUCCESS("\n🏁 Histórico da Dinamarca importado com sucesso!"))
