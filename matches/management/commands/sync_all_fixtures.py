"""
Universal fixture sync command - syncs upcoming matches for all or specific leagues
Includes team validation to prevent cross-league contamination
Usage: 
  python manage.py sync_all_fixtures --days 14
  python manage.py sync_all_fixtures --league "Premier League" --days 7
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from matches.models import League, Season, Team, Match
from matches.api_manager import APIManager
from matches.team_validation import is_team_valid_for_league

class Command(BaseCommand):
    help = 'Sync upcoming fixtures for all leagues with team validation'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=14, help='Days ahead to fetch')
        parser.add_argument('--league', type=str, help='Specific league name (optional)')
        parser.add_argument('--force', action='store_true', help='Force run in DEBUG mode')

    def handle(self, *args, **options):
        if settings.DEBUG and not options['force']:
            self.stdout.write(self.style.ERROR("ERROR: Use --force in DEBUG mode"))
            return

        days_ahead = options['days']
        league_filter = options.get('league')
        
        # Define leagues to sync with country to avoid duplicates
        leagues_to_sync = [
            {'name': 'Premier League', 'country': 'Inglaterra'},
            {'name': 'La Liga', 'country': 'Espanha'},
            {'name': 'Bundesliga', 'country': 'Alemanha'},  # Not Austria!
            {'name': 'Serie A', 'country': 'Italia'},
            {'name': 'Ligue 1', 'country': 'Franca'},
            {'name': 'Brasileirao', 'country': 'Brasil'},
            {'name': 'Pro League', 'country': 'Belgica'},
        ]
        
        if league_filter:
            # If user specifies a league, try to find it (without country filter)
            leagues_to_sync = [{'name': league_filter, 'country': None}]
        
        self.stdout.write(self.style.SUCCESS(f'\n🔄 Syncing fixtures for {len(leagues_to_sync)} league(s)...\n'))
        
        api_manager = APIManager()
        current_year = timezone.now().year
        season, _ = Season.objects.get_or_create(year=current_year)
        
        total_created = 0
        total_updated = 0
        total_skipped = 0
        
        for league_config in leagues_to_sync:
            league_name = league_config['name']
            league_country = league_config.get('country')
            
            self.stdout.write(f'\n📊 {league_name}')
            if league_country:
                self.stdout.write(f'   ({league_country})')
            self.stdout.write('-' * 50)
            
            # Filter by name and country to avoid duplicates (e.g., Bundesliga Germany vs Austria)
            if league_country:
                league = League.objects.filter(name=league_name, country=league_country).first()
            else:
                league = League.objects.filter(name=league_name).first()
            
            if not league:
                self.stdout.write(self.style.WARNING(f'  ⚠️  League not found, skipping'))
                continue
            
            try:
                # Fetch from API
                fixtures = api_manager.get_upcoming_fixtures(
                    league_name=league_name,
                    days_ahead=days_ahead
                )
                
                self.stdout.write(f'  📥 API returned {len(fixtures)} fixtures')
                
                created, updated, skipped = self._process_fixtures(
                    fixtures, league, season
                )
                
                total_created += created
                total_updated += updated
                total_skipped += skipped
                
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Created: {created}, Updated: {updated}, Skipped: {skipped}'
                ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Error: {e}'))
                continue
        
        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('✅ SYNC COMPLETE'))
        self.stdout.write(f'  Total Created: {total_created}')
        self.stdout.write(f'  Total Updated: {total_updated}')
        self.stdout.write(f'  Total Skipped: {total_skipped}')

    def _process_fixtures(self, fixtures, league, season):
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for fixture_data in fixtures:
            # CRITICAL: Validate team names against whitelist BEFORE processing
            home_team_name = fixture_data['home_team']
            away_team_name = fixture_data['away_team']
            
            if not is_team_valid_for_league(home_team_name, league.name):
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Rejected: {home_team_name} not valid for {league.name}'
                ))
                skipped_count += 1
                continue
            
            if not is_team_valid_for_league(away_team_name, league.name):
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Rejected: {away_team_name} not valid for {league.name}'
                ))
                skipped_count += 1
                continue
            
            # Get or create teams
            home_team = self._get_or_create_team(
                home_team_name, 
                league,
                fixture_data.get('home_team_id')
            )
            away_team = self._get_or_create_team(
                away_team_name, 
                league,
                fixture_data.get('away_team_id')
            )
            
            if not home_team or not away_team:
                skipped_count += 1
                continue
            
            # CRITICAL: Validate teams belong to this league
            if home_team.league != league or away_team.league != league:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Team league mismatch: {home_team.name} ({home_team.league.name}) vs '
                    f'{away_team.name} ({away_team.league.name}) - Expected: {league.name}'
                ))
                skipped_count += 1
                continue
            
            # Parse date
            match_date = timezone.datetime.fromisoformat(
                fixture_data['date'].replace('Z', '+00:00')
            )
            
            # Create or update match
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
            else:
                updated_count += 1
        
        return created_count, updated_count, skipped_count

    def _get_or_create_team(self, team_name, league, api_team_id=None):
        """Get or create team with strict league validation"""
        
        # Team name mappings
        name_mapping = {
            # Premier League
            'Manchester United': 'Manchester Utd',
            'Manchester United FC': 'Manchester Utd',
            'Newcastle United': 'Newcastle Utd',
            'West Ham United': 'West Ham Utd',
            'Wolverhampton Wanderers': 'Wolverhampton',
            'Nottingham Forest': 'Nottm Forest',
            'Brighton & Hove Albion': 'Brighton',
            'Tottenham Hotspur': 'Tottenham',
            'Leeds United': 'Leeds Utd',
            
            # Belgium
            'Royal Antwerp FC': 'Antwerp',
            'KV Mechelen': 'Mechelen',
            'KRC Genk': 'Genk',
            'RSC Anderlecht': 'Anderlecht',
            'Club Brugge KV': 'Club Brugge',
            'KAA Gent': 'Gent',
            'Standard Liège': 'Standard Liege',
            'Sint-Truidense VV': 'Sint-Truiden',
            'Union Saint-Gilloise': 'Royale Union SG',
            'Cercle Brugge KSV': 'Cercle Brugge',
        }
        
        db_name = name_mapping.get(team_name, team_name)
        
        # Try exact match in this league only
        team = Team.objects.filter(name=db_name, league=league).first()
        
        if not team:
            # Try case-insensitive
            team = Team.objects.filter(name__iexact=db_name, league=league).first()
        
        if not team:
            # Try partial match (first word) in this league only
            first_word = db_name.split()[0]
            team = Team.objects.filter(
                name__icontains=first_word, 
                league=league
            ).first()
        
        if not team:
            # Create new team ONLY for this league
            team = Team.objects.create(name=db_name, league=league)
            self.stdout.write(self.style.WARNING(f'    [NEW] {db_name} in {league.name}'))
        
        return team
