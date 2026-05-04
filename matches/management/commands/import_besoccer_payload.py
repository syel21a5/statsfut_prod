import json
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import Match, League, Team, Season
from matches.utils import normalize_team_name
from datetime import datetime

class Command(BaseCommand):
    help = 'Importa placares ao vivo do BeSoccer via payload JSON'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Caminho do arquivo payload.json')

    def handle(self, *args, **options):
        file_path = options['file']
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {file_path}'))
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count_updated = 0
        now = timezone.now()
        current_year = now.year
        season_obj, _ = Season.objects.get_or_create(year=current_year)

        for item in data:
            try:
                league_name = item.get('league')
                country = item.get('country')
                home_name = normalize_team_name(item.get('home_team'))
                away_name = normalize_team_name(item.get('away_team'))
                score_home = item.get('home_score')
                score_away = item.get('away_score')
                status = item.get('status', 'Live')
                elapsed = item.get('elapsed')

                # Tenta encontrar a liga
                league = None
                if league_name != "Desconhecida":
                    league = League.objects.filter(name__icontains=league_name, country__icontains=country).first()
                
                # Busca o jogo que está acontecendo hoje ou recentemente
                # Se temos a liga, usamos ela. Se não, buscamos apenas pelos times (mais flexível)
                if league:
                    match_query = Match.objects.filter(
                        league=league,
                        home_team__name=home_name,
                        away_team__name=away_name,
                        status__in=['Scheduled', 'Live', '1H', '2H', 'HT', 'In Play']
                    )
                else:
                    match_query = Match.objects.filter(
                        home_team__name=home_name,
                        away_team__name=away_name,
                        status__in=['Scheduled', 'Live', '1H', '2H', 'HT', 'In Play']
                    )

                match = match_query.order_by('-date').first()

                if match:
                    # Atualiza placar e status
                    match.home_score = score_home
                    match.away_score = score_away
                    match.status = status
                    
                    try:
                        # Converte minuto para inteiro se possível
                        match.elapsed_time = int(elapsed)
                    except (ValueError, TypeError):
                        if elapsed == "FT":
                            match.elapsed_time = 90
                            match.status = "Finished"
                        elif elapsed == "HT":
                            match.elapsed_time = 45
                            match.status = "HT"
                        else:
                            match.elapsed_time = None

                    match.save()
                    count_updated += 1
                    self.stdout.write(f"✅ Atualizado: {home_name} {score_home}-{score_away} {away_name} ({elapsed}')")
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Erro ao processar item: {e}"))

        self.stdout.write(self.style.SUCCESS(f'Sucesso: {count_updated} jogos atualizados via BeSoccer.'))
