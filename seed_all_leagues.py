import os
import django
import sys

# Setup Django environment
sys.path.append('e:\\GitHub\\statsfut\\statsfut')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League
from matches.utils import COUNTRY_REVERSE_TRANSLATIONS

# List of countries extracted from base.html flags
# Key: Slug used in URL (e.g. 'argentina')
# Value: Likely league name (generic) to create if missing
COUNTRIES_TO_SEED = [
    'argentina', 'austria', 'australia', 'belgium', 'brazil', 'switzerland',
    'czech-republic', 'germany', 'denmark', 'england', 'spain', 'finland',
    'france', 'greece', 'netherlands', 'italy', 'japan', 'norway', 'poland',
    'portugal', 'russia', 'sweden', 'turkey', 'ukraine'
]

print("--- Seeding Missing Countries ---")
count_created = 0

for slug in COUNTRIES_TO_SEED:
    # 1. Get Portuguese Name
    slug_clean = slug.replace('-', ' ')
    pt_country = COUNTRY_REVERSE_TRANSLATIONS.get(slug_clean.lower())
    
    if not pt_country:
        pt_country = slug_clean.title()
        print(f"Warning: No translation found for '{slug}'. Using '{pt_country}'.")

    # 2. Check if ANY league exists for this country
    exists = League.objects.filter(country__iexact=pt_country).exists()
    
    if not exists:
        # Create a generic league
        league_name = f"League {pt_country}"
        if pt_country == 'Inglaterra': league_name = 'Premier League'
        elif pt_country == 'Brasil': league_name = 'Brasileirão'
        elif pt_country == 'Espanha': league_name = 'La Liga'
        elif pt_country == 'Italia': league_name = 'Serie A'
        elif pt_country == 'Alemanha': league_name = 'Bundesliga'
        elif pt_country == 'Franca': league_name = 'Ligue 1'
        
        print(f"Creating generic league for: {pt_country} ({league_name})")
        League.objects.create(name=league_name, country=pt_country)
        count_created += 1
    else:
        print(f"Country exists: {pt_country} - OK")

print(f"\n--- Finished. Created {count_created} new entries. ---")
