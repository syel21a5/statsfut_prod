"""
Simple Belgium fixtures importer using Football-Data.org API
Since API-Football doesn't work well for Belgium, we use Football-Data.org
Usage: python manage.py import_belgium_fixtures
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import League, Season, Team, Match
from matches.api_manager import APIManager

class Command(BaseCommand):
    help = 'Import Belgium fixtures from Football-Data.org'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force run in DEBUG mode')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n📊 Importing Belgium fixtures...\n'))
        
        # Get or create league
        league, _ = League.objects.get_or_create(
            name='Pro League',
            defaults={'country': 'Belgica'}
        )
        
        # Get current season
        current_year = timezone.now().year
        season, _ = Season.objects.get_or_create(year=current_year)
        
        # Use APIManager to fetch fixtures
        api_manager = APIManager()
        
        try:
            # Try to get upcoming fixtures
            self.stdout.write('Fetching upcoming fixtures...')
            fixtures = api_manager.get_upcoming_fixtures(
                league_name='Pro League',
                days_ahead=30
            )
            
            self.stdout.write(f'API returned {len(fixtures)} fixtures')
            
            # Belgian team names from whitelist
            belgian_teams = [
                'Royale Union SG', 'Union SG', 'Union Saint-Gilloise',
                'Sint-Truiden', 'Sint-Truidense VV',
                'Club Brugge', 'Club Brugge KV',
                'Gent', 'KAA Gent',
                'Mechelen', 'KV Mechelen',
                'Genk', 'KRC Genk',
                'Anderlecht', 'RSC Anderlecht',
                'Charleroi', 'Sporting Charleroi',
                'Westerlo', 'KVC Westerlo',
                'Antwerp', 'Royal Antwerp FC',
                'Zulte-Waregem', 'Zulte Waregem',
                'Standard Liege', 'Standard Liège',
                'OH Leuven', 'Oud-Heverlee Leuven',
                'La Louviere', 'RWDM Brussels',
                'Cercle Brugge', 'Cercle Brugge KSV',
                'Dender', 'FCV Dender EH',
            ]
            
            created = 0
            updated = 0
            skipped = 0
            
            for fixture in fixtures:
                home_name = fixture['home_team']
                away_name = fixture['away_team']
                
                # Validate Belgian teams
                home_valid = any(bt.lower() in home_name.lower() or home_name.lower() in bt.lower() for bt in belgian_teams)
                away_valid = any(bt.lower() in away_name.lower() or away_name.lower() in bt.lower() for bt in belgian_teams)
                
                if not home_valid or not away_valid:
                    self.stdout.write(self.style.WARNING(f'  ⚠️  Skipped: {home_name} vs {away_name}'))
                    skipped += 1
                    continue
                
                # Get or create teams
                home_team, _ = Team.objects.get_or_create(
                    name=home_name,
                    defaults={'league': league}
                )
                away_team, _ = Team.objects.get_or_create(
                    name=away_name,
                    defaults={'league': league}
                )
                
                # Parse date
                match_date = timezone.datetime.fromisoformat(
                    fixture['date'].replace('Z', '+00:00')
                )
                
                # Create or update match
                api_id = f"API_{fixture['id']}"
                match, is_created = Match.objects.update_or_create(
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
                
                if is_created:
                    created += 1
                    self.stdout.write(f'  ✓ Created: {home_name} vs {away_name}')
                else:
                    updated += 1
            
            self.stdout.write('\n' + '=' * 50)
            self.stdout.write(self.style.SUCCESS('✅ IMPORT COMPLETE'))
            self.stdout.write(f'  Created: {created}')
            self.stdout.write(f'  Updated: {updated}')
            self.stdout.write(f'  Skipped: {skipped}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
