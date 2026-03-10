import csv
import os
from django.core.management.base import BaseCommand
from matches.models import League, Match, Season

class Command(BaseCommand):
    help = "Exporta os jogos de uma liga/temporada para a pasta historical_data"

    def add_arguments(self, parser):
        parser.add_argument("--league", type=str, required=True)
        parser.add_argument("--year", type=int, required=True)

    def handle(self, *args, **options):
        league_name = options["league"]
        year = options["year"]
        
        output_dir = "historical_data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        filename = os.path.join(output_dir, f"{league_name}_{year}_backup.csv")
        
        matches = Match.objects.filter(league__name=league_name, season__year=year).order_by("date")
        
        if not matches.exists():
            self.stdout.write(self.style.ERROR(f"Nenhum jogo encontrado para {league_name} {year}"))
            return

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "HomeTeam", "AwayTeam", "HomeScore", "AwayScore", "Status"])
            for m in matches:
                writer.writerow([
                    m.date,
                    m.home_team.name,
                    m.away_team.name,
                    m.home_score,
                    m.away_score,
                    m.status
                ])
        
        self.stdout.write(self.style.SUCCESS(f"✅ Exportado: {filename}"))
