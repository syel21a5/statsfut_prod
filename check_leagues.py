import os
import django
import sys

# Setup Django environment
sys.path.append('e:\\GitHub\\statsfut\\statsfut')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League
from matches.utils import COUNTRY_REVERSE_TRANSLATIONS

print("--- Existing Leagues in DB ---")
leagues = League.objects.all()
for l in leagues:
    print(f"ID: {l.id} | Name: {l.name} | Country: {l.country}")

print("\n--- Testing 'England' Lookup ---")
slug = 'england'
db_country = COUNTRY_REVERSE_TRANSLATIONS.get(slug)
print(f"Slug: {slug} -> DB Country: {db_country}")

if db_country:
    exists = League.objects.filter(country__iexact=db_country).exists()
    print(f"Exists in DB as '{db_country}': {exists}")
else:
    print("No translation found.")
