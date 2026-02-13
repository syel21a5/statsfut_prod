import os
import django
import sys

# Setup Django environment
sys.path.append('e:\\GitHub\\statsfut\\statsfut')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League
from matches.utils import COUNTRY_REVERSE_TRANSLATIONS, COUNTRY_TRANSLATIONS

print("--- Starting Country Name Fix ---")

# Invert dictionary to get English -> Portuguese
# The utils.py has COUNTRY_TRANSLATIONS as Portuguese -> English
# So we need English -> Portuguese map
ENG_TO_PT = {v: k for k, v in COUNTRY_TRANSLATIONS.items()}

leagues = League.objects.all()
count_fixed = 0

for l in leagues:
    current_country = l.country
    
    # Check if current country is in English (i.e. it is a value in COUNTRY_TRANSLATIONS)
    # But we want the Portuguese key.
    
    if current_country in ENG_TO_PT:
        new_country = ENG_TO_PT[current_country]
        print(f"Fixing League '{l.name}': '{current_country}' -> '{new_country}'")
        l.country = new_country
        l.save()
        count_fixed += 1
    elif current_country in COUNTRY_TRANSLATIONS:
         print(f"League '{l.name}' already has Portuguese country: '{current_country}' - OK")
    else:
        print(f"League '{l.name}' has unknown country: '{current_country}' - Manual check needed?")

print(f"\n--- Finished. Fixed {count_fixed} leagues. ---")
