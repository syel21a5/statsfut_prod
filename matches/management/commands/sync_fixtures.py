"""
Management command para sincronizar fixtures da API
Uso: python manage.py sync_fixtures
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from matches.models import League, Season, Team, Match
from matches.api_manager import APIManager

class Command(BaseCommand):
    help = 'Sincroniza fixtures (jogos futuros) da API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=14,
            help='Número de dias à frente para buscar fixtures (padrão: 14)'
        )
        parser.add_argument(
            '--league',
            type=str,
            default='Premier League',
            help='Nome da liga (padrão: Premier League)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força execução mesmo em DEBUG'
        )

    def handle(self, *args, **options):
        if settings.DEBUG and not options['force']:
            self.stdout.write(self.style.ERROR("ERRO: Este comando consome API e não deve ser executado em ambiente de desenvolvimento (DEBUG=True). Use --force se realmente necessário."))
            return

        days_ahead = options['days']
        league_name = options['league']
        
        self.stdout.write(f"Sincronizando fixtures dos próximos {days_ahead} dias para {league_name}...")
        
        # Get league
        try:
            league = League.objects.get(name=league_name)
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Liga "{league_name}" não encontrada'))
            return
        
        # Get current season
        current_year = timezone.now().year
        season, _ = Season.objects.get_or_create(year=current_year)
        
        # Initialize API Manager
        api_manager = APIManager()
        
        try:
            # Fetch upcoming fixtures from API
            self.stdout.write("Buscando fixtures da API...")
            fixtures = api_manager.get_upcoming_fixtures(
                league_name=league_name,
                days_ahead=days_ahead
            )
            
            self.stdout.write(f"Encontrados {len(fixtures)} fixtures")
            
            # Process each fixture
            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            for fixture_data in fixtures:
                # Map team names to database teams
                home_team = self._get_or_create_team(fixture_data['home_team'], league)
                away_team = self._get_or_create_team(fixture_data['away_team'], league)
                
                if not home_team or not away_team:
                    self.stdout.write(self.style.WARNING(
                        f"Pulando: {fixture_data['home_team']} vs {fixture_data['away_team']} (time não encontrado)"
                    ))
                    skipped_count += 1
                    continue
                
                # Parse date
                match_date = timezone.datetime.fromisoformat(fixture_data['date'].replace('Z', '+00:00'))
                
                # Check if match already exists
                api_id = f"API_{fixture_data['id']}"
                
                match, created = Match.objects.update_or_create(
                    api_id=api_id,
                    defaults={
                        'league': league,
                        'season': season,
                        'home_team': home_team,
                        'away_team': away_team,
                        'date': match_date,
                        'status': 'Scheduled',
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f"  ✓ Criado: {home_team.name} vs {away_team.name} ({match_date.strftime('%d/%m %H:%M')})")
                else:
                    updated_count += 1
                    self.stdout.write(f"  ↻ Atualizado: {home_team.name} vs {away_team.name}")
            
            # Summary
            self.stdout.write(self.style.SUCCESS(f'\n✅ Sincronização concluída!'))
            self.stdout.write(f"  • Criados: {created_count}")
            self.stdout.write(f"  • Atualizados: {updated_count}")
            self.stdout.write(f"  • Pulados: {skipped_count}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao buscar fixtures: {e}'))
    
    def _get_or_create_team(self, team_name, league):
        """
        Tenta encontrar o time no banco ou criar se não existir
        """
        # Mapeamento completo de nomes da API para nomes do banco
        name_mapping = {
            # Manchester teams
            'Manchester United': 'Manchester Utd',
            'Manchester United FC': 'Manchester Utd',
            'Man United': 'Manchester Utd',
            'Manchester City': 'Manchester City',
            'Manchester City FC': 'Manchester City',
            'Man City': 'Manchester City',
            
            # London teams
            'Tottenham': 'Tottenham',
            'Tottenham Hotspur': 'Tottenham',
            'Tottenham Hotspur FC': 'Tottenham',
            'Spurs': 'Tottenham',
            'Chelsea': 'Chelsea',
            'Chelsea FC': 'Chelsea',
            'Arsenal': 'Arsenal',
            'Arsenal FC': 'Arsenal',
            'West Ham': 'West Ham Utd',
            'West Ham United': 'West Ham Utd',
            'West Ham United FC': 'West Ham Utd',
            'Crystal Palace': 'Crystal Palace',
            'Crystal Palace FC': 'Crystal Palace',
            'Fulham': 'Fulham',
            'Fulham FC': 'Fulham',
            'Brentford': 'Brentford',
            'Brentford FC': 'Brentford',
            
            # Other teams
            'Newcastle': 'Newcastle Utd',
            'Newcastle United': 'Newcastle Utd',
            'Newcastle United FC': 'Newcastle Utd',
            'Wolves': 'Wolverhampton',
            'Wolverhampton': 'Wolverhampton',
            'Wolverhampton Wanderers': 'Wolverhampton',
            'Wolverhampton Wanderers FC': 'Wolverhampton',
            'Nottingham Forest': 'Nottm Forest',
            'Nottingham Forest FC': 'Nottm Forest',
            "Nott'm Forest": 'Nottm Forest',
            'Leeds': 'Leeds Utd',
            'Leeds United': 'Leeds Utd',
            'Leeds United FC': 'Leeds Utd',
            'Liverpool': 'Liverpool',
            'Liverpool FC': 'Liverpool',
            'Aston Villa': 'Aston Villa',
            'Aston Villa FC': 'Aston Villa',
            'Everton': 'Everton',
            'Everton FC': 'Everton',
            'Brighton': 'Brighton',
            'Brighton & Hove Albion': 'Brighton',
            'Brighton & Hove Albion FC': 'Brighton',
            'Brighton and Hove Albion': 'Brighton',
            'Bournemouth': 'Bournemouth',
            'AFC Bournemouth': 'Bournemouth',
            'Burnley': 'Burnley',
            'Burnley FC': 'Burnley',
            'Sunderland': 'Sunderland',
            'Sunderland AFC': 'Sunderland',
        }
        
        # Try exact mapping first
        db_name = name_mapping.get(team_name, team_name)
        
        # Try exact match
        team = Team.objects.filter(name=db_name, league=league).first()
        
        if not team:
            # Try case-insensitive match
            team = Team.objects.filter(name__iexact=db_name, league=league).first()
        
        if not team:
            # Try partial match (first word)
            first_word = db_name.split()[0]
            team = Team.objects.filter(name__icontains=first_word, league=league).first()
        
        if not team:
            # Create new team only if really doesn't exist
            team = Team.objects.create(name=db_name, league=league)
            self.stdout.write(self.style.WARNING(f"  [NOVO TIME] {db_name}"))
        
        return team
