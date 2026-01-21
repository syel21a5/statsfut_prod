import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match

now = timezone.now()
matches = Match.objects.filter(date__date=now.date())
print(f'Jogos de hoje ({now.date()}): {matches.count()}')
for m in matches:
    print(f'- {m.home_team} x {m.away_team} ({m.status}) at {m.date}')
