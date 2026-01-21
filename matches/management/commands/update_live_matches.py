from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from matches.api_manager import APIManager
from django.utils import timezone
from datetime import datetime
import pytz

class Command(BaseCommand):
    help = 'Atualiza jogos ao vivo e próximos jogos usando as APIs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='both',
            help='Modo: live (ao vivo), upcoming (próximos), ou both (ambos)'
        )

    def handle(self, *args, **options):
        mode = options['mode']
        
        api_manager = APIManager()
        
        # IDs das ligas na API-Football
        # 39 = Premier League
        # 71 = Brasileirão Série A
        league_ids = [39, 71]
        
        if mode in ['live', 'both']:
            self.stdout.write(self.style.SUCCESS('🔴 Buscando jogos AO VIVO...'))
            try:
                live_fixtures = api_manager.get_live_fixtures(league_ids=league_ids)
                self.process_fixtures(live_fixtures, is_live=True)
                self.stdout.write(self.style.SUCCESS(f'✅ {len(live_fixtures)} jogos ao vivo processados'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro ao buscar jogos ao vivo: {e}'))
        
        if mode in ['upcoming', 'both']:
            self.stdout.write(self.style.SUCCESS('📅 Buscando próximos jogos (14 dias)...'))
            try:
                upcoming_fixtures = api_manager.get_upcoming_fixtures(league_ids=league_ids, days_ahead=14)
                self.process_fixtures(upcoming_fixtures, is_live=False)
                self.stdout.write(self.style.SUCCESS(f'✅ {len(upcoming_fixtures)} próximos jogos processados'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro ao buscar próximos jogos: {e}'))

    def process_fixtures(self, fixtures, is_live=False):
        """Processa fixtures e salva/atualiza no banco"""
        
        count_new = 0
        count_updated = 0
        
        for fixture in fixtures:
            try:
                # Mapeia nome da liga
                league_name_map = {
                    'Premier League': 'Premier League',
                    'Brasileirão Série A': 'Brasileirão',
                    'Serie A': 'Brasileirão',
                }
                
                league_name = league_name_map.get(fixture['league'], fixture['league'])
                
                # Busca ou cria liga
                if 'Premier' in league_name:
                    league_obj, _ = League.objects.get_or_create(
                        name='Premier League',
                        country='Inglaterra'
                    )
                elif 'Brasil' in league_name or 'Serie A' in league_name:
                    league_obj, _ = League.objects.get_or_create(
                        name='Brasileirão',
                        country='Brasil'
                    )
                else:
                    continue  # Pula ligas desconhecidas
                
                # Busca ou cria times
                if 'Manchester' in fixture['home_team'] or 'Manchester' in fixture['away_team']:
                    print(f"DEBUG: Processing {fixture['home_team']} (ID: {fixture.get('home_team_id')}) vs {fixture['away_team']} (ID: {fixture.get('away_team_id')})")

                # Mapping names from Football-Data.org to local DB
                name_mapping = {
                    'Manchester United FC': 'Manchester Utd',
                    'Manchester City FC': 'Manchester City',
                    'West Ham United FC': 'West Ham',
                    'Newcastle United FC': 'Newcastle',
                    'Tottenham Hotspur FC': 'Tottenham',
                    'Wolverhampton Wanderers FC': 'Wolves',
                    'Leicester City FC': 'Leicester',
                    'Leeds United FC': 'Leeds',
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
                    'Sheffield United FC': 'Sheffield United',
                    'Burnley FC': 'Burnley',
                    'Luton Town FC': 'Luton',
                    'Norwich City FC': 'Norwich',
                    'Watford FC': 'Watford',
                }
                
                home_name = fixture['home_team']
                away_name = fixture['away_team']
                
                home_name = name_mapping.get(home_name, home_name)
                away_name = name_mapping.get(away_name, away_name)

                home_team, _ = Team.objects.get_or_create(
                    name=home_name,
                    league=league_obj,
                    defaults={'api_id': str(fixture.get('home_team_id')) if fixture.get('home_team_id') else None}
                )
                
                # Se já existia, atualiza o api_id se não estiver setado
                if not home_team.api_id and fixture.get('home_team_id'):
                    home_team.api_id = str(fixture.get('home_team_id'))
                    home_team.save()
                
                away_team, _ = Team.objects.get_or_create(
                    name=away_name,
                    league=league_obj,
                    defaults={'api_id': str(fixture.get('away_team_id')) if fixture.get('away_team_id') else None}
                )

                if not away_team.api_id and fixture.get('away_team_id'):
                    away_team.api_id = str(fixture.get('away_team_id'))
                    away_team.save()
                
                # Parse data
                try:
                    match_date = datetime.fromisoformat(fixture['date'].replace('Z', '+00:00'))
                    if timezone.is_naive(match_date):
                        match_date = timezone.make_aware(match_date, pytz.UTC)
                except:
                    match_date = None
                
                # Determina temporada (ano de término)
                if match_date:
                    year = match_date.year
                    # Se for entre Jan-Jul, é temporada do ano atual
                    # Se for Ago-Dez, é temporada do ano seguinte
                    if match_date.month >= 8:
                        season_year = year + 1
                    else:
                        season_year = year
                else:
                    season_year = datetime.now().year
                
                season_obj, _ = Season.objects.get_or_create(year=season_year)
                
                # Determina status
                status_map = {
                    'NS': 'Scheduled',  # Not Started
                    'LIVE': 'Live',
                    '1H': 'Live',  # First Half
                    'HT': 'Live',  # Half Time
                    '2H': 'Live',  # Second Half
                    'FT': 'Finished',  # Full Time
                    'AET': 'Finished',  # After Extra Time
                    'PEN': 'Finished',  # Penalties
                    'PST': 'Postponed',
                    'CANC': 'Cancelled',
                    'ABD': 'Abandoned',
                    'SCHEDULED': 'Scheduled',
                    'IN_PLAY': 'Live',
                    'FINISHED': 'Finished',
                }
                
                status = status_map.get(fixture['status'], 'Scheduled')
                
                # Dados para salvar
                defaults = {
                    'date': match_date,
                    'status': status,
                    'home_score': fixture['home_score'],
                    'away_score': fixture['away_score'],
                    'elapsed_time': fixture.get('elapsed'),
                    'api_id': str(fixture['id']) if fixture.get('id') else None
                }
                
                # Tenta encontrar jogo existente
                # Incluímos api_id no update, mas para evitar duplicatas erradas,
                # o ideal seria usar api_id no lookup se já existir, mas vamos manter
                # a lógica de times/data por enquanto e apenas enriquecer com o ID.
                match_obj, created = Match.objects.update_or_create(
                    league=league_obj,
                    season=season_obj,
                    home_team=home_team,
                    away_team=away_team,
                    defaults=defaults
                )
                
                if created:
                    count_new += 1
                    self.stdout.write(f'  ➕ Novo: {home_team.name} vs {away_team.name}')
                else:
                    count_updated += 1
                    if is_live:
                        self.stdout.write(f'  🔄 Atualizado: {home_team.name} {fixture["home_score"]}-{fixture["away_score"]} {away_team.name} ({fixture.get("elapsed", "?")}\')')
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Erro ao processar fixture: {e}'))
                continue
        
        self.stdout.write(f'📊 Resumo: {count_new} novos, {count_updated} atualizados')
