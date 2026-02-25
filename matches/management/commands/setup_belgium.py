import os
import csv
import requests
from io import StringIO
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import League, Team, Match, Season
from django.conf import settings

# Mapeamento para padronizar nomes conforme SoccerStats
TEAM_MAPPING = {
    "Union SG": "Royale Union SG",
    "Union Saint-Gilloise": "Royale Union SG",
    "St. Gilloise": "Royale Union SG",
    "Union St.Gilloise": "Royale Union SG",
    "St Truiden": "Sint-Truiden",
    "St. Truiden": "Sint-Truiden",
    "Mechelen": "KV Mechelen",
    "Genk": "KRC Genk",
    "Standard": "Standard Liege",
    "Standard Liège": "Standard Liege",
    "Zulte Waregem": "Zulte-Waregem",
    "Waregem": "Zulte-Waregem",
    "Leuven": "OH Leuven",
    "Oud-Heverlee Leuven": "OH Leuven",
    "Kortrijk": "KV Kortrijk",
    "Beerschot VA": "Beerschot",
    "Beerschot-Wilrijk": "Beerschot",
    "Ostend": "KV Oostende",
    "Oostende": "KV Oostende",
    "Mouscron": "Mouscron-Peruwelz",
}

class Command(BaseCommand):
    help = 'Setup Belgium Pro League: Download CSVs (2016-2025) and Import Data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🇧🇪 Iniciando Setup da Bélgica (Pro League)...'))

        # 1. Configurar Liga
        league_name = 'Pro League'
        country_name = 'Belgica'
        league, created = League.objects.get_or_create(
            name=league_name,
            defaults={'country': country_name}
        )
        if created:
            self.stdout.write(f'✅ Liga criada: {league_name}')
        else:
            self.stdout.write(f'ℹ️ Liga já existe: {league_name}')

        # 2. Definir temporadas para baixar (1617 a 2425)
        # 1617 = 2016/2017 -> Season 2017 (fim)
        seasons_codes = [
            ('1617', 2017),
            ('1718', 2018),
            ('1819', 2019),
            ('1920', 2020),
            ('2021', 2021),
            ('2122', 2022),
            ('2223', 2023),
            ('2324', 2024),
            ('2425', 2025),
        ]
        
        # Ajuste: No sistema, season usually refers to the year it ends or the main year.
        # Vou usar o ano final da temporada como referência.
        
        base_url = "https://www.football-data.co.uk/mmz4281/{}/B1.csv"

        for code, year in seasons_codes:
            url = base_url.format(code)
            self.stdout.write(f'\n⬇️ Baixando {code} ({year})... URL: {url}')
            
            try:
                response = requests.get(url, timeout=30)
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f'❌ Erro {response.status_code} ao baixar {url}'))
                    continue
                
                content = response.content.decode('utf-8', errors='replace')
                csv_file = StringIO(content)
                reader = csv.DictReader(csv_file)
                
                season_obj, _ = Season.objects.get_or_create(year=year)
                
                count = 0
                for row in reader:
                    if not row.get('Date'):
                        continue
                        
                    try:
                        # Parse Date (dd/mm/yy or dd/mm/yyyy)
                        date_str = row['Date']
                        try:
                            date_obj = timezone.datetime.strptime(date_str, "%d/%m/%y")
                        except ValueError:
                            date_obj = timezone.datetime.strptime(date_str, "%d/%m/%Y")
                            
                        # Add Time if available
                        if row.get('Time'):
                            time_str = row['Time']
                            hour, minute = map(int, time_str.split(':'))
                            date_obj = date_obj.replace(hour=hour, minute=minute)
                        else:
                            date_obj = date_obj.replace(hour=12, minute=0) # Default time
                            
                        date_obj = timezone.make_aware(date_obj)
                        
                        # Teams
                        raw_home_team = row['HomeTeam'].strip()
                        raw_away_team = row['AwayTeam'].strip()
                        
                        if not raw_home_team or not raw_away_team:
                            continue
                            
                        # Apply Mapping
                        home_team_name = TEAM_MAPPING.get(raw_home_team, raw_home_team)
                        away_team_name = TEAM_MAPPING.get(raw_away_team, raw_away_team)

                        home_team, created_h = Team.objects.get_or_create(name=home_team_name, league=league)
                        if created_h:
                            self.stdout.write(f"  + Novo Time: {home_team_name} (Raw: {raw_home_team})")
                        
                        away_team, created_a = Team.objects.get_or_create(name=away_team_name, league=league)
                        if created_a:
                            self.stdout.write(f"  + Novo Time: {away_team_name} (Raw: {raw_away_team})")
                        
                        # Scores
                        fthg = row.get('FTHG')
                        ftag = row.get('FTAG')
                        
                        if fthg is None or ftag is None or fthg == '' or ftag == '':
                            status = 'Scheduled'
                            home_score = 0
                            away_score = 0
                        else:
                            status = 'Finished'
                            home_score = int(fthg)
                            away_score = int(ftag)
                            
                        # Create/Update Match
                        match, created_match = Match.objects.update_or_create(
                            league=league,
                            season=season_obj,
                            home_team=home_team,
                            away_team=away_team,
                            date=date_obj,
                            defaults={
                                'home_score': home_score,
                                'away_score': away_score,
                                'status': status
                            }
                        )
                        count += 1
                        
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  ⚠️ Erro na linha: {e}'))
                        continue
                        
                self.stdout.write(self.style.SUCCESS(f'✅ Importados {count} jogos da temporada {year}'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Falha geral na temporada {code}: {e}'))

        self.stdout.write(self.style.SUCCESS('\n🇧🇪 Setup da Bélgica concluído!'))
