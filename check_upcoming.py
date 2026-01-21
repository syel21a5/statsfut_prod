import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match

now = timezone.now()
upcoming = Match.objects.filter(date__gte=now).order_by('date')
print(f'Próximos jogos: {upcoming.count()}')
for m in upcoming[:10]:
    print(f'- {m.home_team} x {m.away_team} em {m.date} ({m.status})')
