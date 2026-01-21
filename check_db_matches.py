import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match

matches = Match.objects.filter(league__name='Premier League').order_by('-date')[:5]
print("Premier League matches:")
for m in matches:
    print(f'- {m.home_team} x {m.away_team} em {m.date} ({m.status})')

now = timezone.now()
print(f"\nTimezone Now: {now}")
print(f"Date range for today used in HomeView: {now.replace(hour=0, minute=0, second=0, microsecond=0)} to {now.replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)}")
