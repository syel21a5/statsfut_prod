"""
Quick check to see if upcoming matches were imported
Usage: python manage.py check_upcoming_matches
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import Match, League
from datetime import timedelta

class Command(BaseCommand):
    help = 'Check upcoming matches in database'

    def handle(self, *args, **options):
        now = timezone.now()
        future = now + timedelta(days=30)
        
        self.stdout.write(self.style.SUCCESS(f'\n📅 Checking upcoming matches (next 30 days)...\n'))
        
        leagues = [
            'Premier League',
            'La Liga',
            'Bundesliga', 
            'Serie A',
            'Ligue 1',
            'Brasileirao',
            'Pro League'
        ]
        
        total_upcoming = 0
        
        for league_name in leagues:
            try:
                league = League.objects.get(name=league_name)
            except League.DoesNotExist:
                self.stdout.write(f'❌ {league_name}: League not found')
                continue
            
            # Count upcoming matches
            upcoming = Match.objects.filter(
                league=league,
                date__gte=now,
                date__lte=future,
                status__in=['Scheduled', 'Not Started', 'TIMED', 'UTC']
            ).order_by('date')
            
            count = upcoming.count()
            total_upcoming += count
            
            if count > 0:
                self.stdout.write(self.style.SUCCESS(f'✅ {league_name}: {count} upcoming matches'))
                # Show first 3
                for m in upcoming[:3]:
                    self.stdout.write(f'   • {m.date.strftime("%d/%m %H:%M")} - {m.home_team.name} vs {m.away_team.name}')
                if count > 3:
                    self.stdout.write(f'   ... and {count - 3} more')
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  {league_name}: 0 upcoming matches'))
        
        self.stdout.write(f'\n📊 Total upcoming matches: {total_upcoming}')
