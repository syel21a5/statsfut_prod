import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team
from django.utils.text import slugify

teams = Team.objects.filter(league__name='Super League', league__country='Suica')
print(f"Total de times: {teams.count()}")
for t in teams:
    print(f"Nome: '{t.name}' -> Slug: '{slugify(t.name)}'")
