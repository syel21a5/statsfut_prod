from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from matches.api_manager import APIManager
from django.utils import timezone
from datetime import datetime, timedelta
import pytz

class Command(BaseCommand):
    help = 'Atualiza resultados recentes (últimos 7 dias) usando a API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Número de dias atrás para buscar resultados (padrão: 7)'
        )

    def handle(self, *args, **options):
        days_back = options['days']
        
        self.stdout.write(self.style.SUCCESS(f'📊 Buscando resultados dos últimos {days_back} dias...'))
        
        api_manager = APIManager()
        
        # Premier League ID na Football-Data.org API
        league_id = 2021
        current_year = datetime.now().year
        
        # Determina o ano da temporada
        if datetime.now().month >= 8:
            season_year = current_year + 1
        else:
            season_year = current_year
        
        try:
            # Busca todos os jogos da temporada atual
            self.stdout.write(f'Buscando jogos da temporada {season_year}...')
            fixtures = api_manager.get_league_season_fixtures(league_id, season_year)
            
            # Filtra apenas jogos finalizados dos últimos X dias
            cutoff_date = timezone.now() - timedelta(days=days_back)
            recent_finished = []
            
            for fixture in fixtures:
                # Verifica se é um jogo finalizado
                if fixture['status'] in ['FINISHED', 'FT', 'AET', 'PEN']:
                    # Parse da data
                    try:
                        match_date = datetime.fromisoformat(fixture['date'].replace('Z', '+00:00'))
                        if timezone.is_naive(match_date):
                            match_date = timezone.make_aware(match_date, pytz.UTC)
                        
                        # Verifica se está dentro do período
                        if match_date >= cutoff_date:
                            recent_finished.append(fixture)
                    except:
                        continue
            
            self.stdout.write(f'✅ Encontrados {len(recent_finished)} jogos finalizados nos últimos {days_back} dias')
            
            # Processa os jogos encontrados
            if recent_finished:
                self._process_fixtures(recent_finished, season_year)
            else:
                self.stdout.write(self.style.WARNING('⚠️  Nenhum jogo recente encontrado'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro ao buscar resultados: {e}'))

    def _process_fixtures(self, fixtures, season_year):
        """Processa e salva fixtures no banco"""
        
        count_new = 0
        count_updated = 0
        
        # Busca ou cria liga
        league_obj, _ = League.objects.get_or_create(
            name='Premier League',
            defaults={'country': 'Inglaterra'}
        )
        
        # Busca ou cria temporada
        season_obj, _ = Season.objects.get_or_create(year=season_year)
        
        # Mapping de nomes
        name_mapping = {
            'Manchester United FC': 'Manchester Utd',
            'Manchester City FC': 'Manchester City',
            'West Ham United FC': 'West Ham',
            'Newcastle United FC': 'Newcastle Utd',
            'Tottenham Hotspur FC': 'Tottenham',
            'Wolverhampton Wanderers FC': 'Wolverhampton',
            'Leicester City FC': 'Leicester',
            'Leeds United FC': 'Leeds Utd',
            'Brighton & Hove Albion FC': 'Brighton',
            'Arsenal FC': 'Arsenal',
            'Chelsea FC': 'Chelsea',
            'Liverpool FC': 'Liverpool',
            'Everton FC': 'Everton',
            'Fulham FC': 'Fulham',
            'Brentford FC': 'Brentford',
            'Crystal Palace FC': 'Crystal Palace',
            'Southampton FC': 'Southampton',
            'Aston Villa FC': 'Aston Villa',
            'Sheffield United FC': 'Sheffield Utd',
            'Burnley FC': 'Burnley',
            'Nottingham Forest FC': 'Nottm Forest',
            'Luton Town FC': 'Luton',
            'AFC Bournemouth': 'Bournemouth',
            'Ipswich Town FC': 'Ipswich',
        }
        
        for fixture in fixtures:
            try:
                home_name = name_mapping.get(fixture['home_team'], fixture['home_team'])
                away_name = name_mapping.get(fixture['away_team'], fixture['away_team'])
                
                # Busca ou cria times
                home_team, _ = Team.objects.get_or_create(
                    name=home_name,
                    defaults={'league': league_obj}
                )
                away_team, _ = Team.objects.get_or_create(
                    name=away_name,
                    defaults={'league': league_obj}
                )
                
                # Parse data
                try:
                    match_date = datetime.fromisoformat(fixture['date'].replace('Z', '+00:00'))
                    if timezone.is_naive(match_date):
                        match_date = timezone.make_aware(match_date, pytz.UTC)
                except:
                    match_date = None
                
                # Determina status
                status_map = {
                    'FINISHED': 'Finished',
                    'FT': 'Finished',
                    'AET': 'Finished',
                    'PEN': 'Finished',
                }
                status = status_map.get(fixture['status'], 'Finished')
                
                # Atualiza ou cria jogo
                match_obj, created = Match.objects.update_or_create(
                    league=league_obj,
                    season=season_obj,
                    home_team=home_team,
                    away_team=away_team,
                    date=match_date,
                    defaults={
                        'status': status,
                        'home_score': fixture['home_score'],
                        'away_score': fixture['away_score'],
                        'api_id': str(fixture['id']) if fixture.get('id') else None
                    }
                )
                
                if created:
                    count_new += 1
                    self.stdout.write(f'  ➕ Novo: {home_team.name} {fixture["home_score"]}-{fixture["away_score"]} {away_team.name}')
                else:
                    count_updated += 1
                    self.stdout.write(f'  🔄 Atualizado: {home_team.name} {fixture["home_score"]}-{fixture["away_score"]} {away_team.name}')
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Erro ao processar {fixture.get("home_team")} vs {fixture.get("away_team")}: {e}'))
                continue
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 Resumo: {count_new} novos, {count_updated} atualizados'))
