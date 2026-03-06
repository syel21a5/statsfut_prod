
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import League, Team

league = League.objects.get(name='Superliga', country='Dinamarca')
print(f"League ID: {league.id}")
teams = Team.objects.filter(league=league).order_by('name')

print(f"{'ID':<6} {'Name':<30}")
print("-" * 40)
for t in teams:
    print(f"{t.id:<6} {t.name:<30}")
