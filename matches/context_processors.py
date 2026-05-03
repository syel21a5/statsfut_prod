from .models import League
from django.utils.text import slugify
from matches.utils import COUNTRY_TRANSLATIONS

from .utils import get_flag_code

def sidebar_context(request):
    """
    Context processor to provide dynamic sidebar data (Leagues grouped by Country).
    """
    leagues = League.objects.exclude(country__iexact='Republica Tcheca').order_by('country', 'name')
    
    # Translation Map (PT -> EN)
    # This is useful if the DB has Portuguese names but we want English display
    country_translations = COUNTRY_TRANSLATIONS

    # Group by Country
    countries_map = {}
    for league in leagues:
        db_country_name = league.country
        
        # Translate name for Display
        display_name = country_translations.get(db_country_name, db_country_name)
        
        # Use English name for grouping/sorting if possible, or fallback to DB name
        group_key = display_name 

        if group_key not in countries_map:
            countries_map[group_key] = {
                'name': display_name,
                'slug': slugify(display_name), # Slugify the English name for consistency
                'leagues': [],
                'flag_code': get_flag_code(display_name) # Use translated name to find flag
            }
        
        # Use slugify on the ORIGINAL DB name for the URL to ensure it matches the DB query in views
        # OR use robust view logic (which we implemented). 
        # Let's stick to slugifying the DB name for the URL param to be safe.
        # UPDATE: Since we want robust matching, passing the slug of the DB name is safer for lookup.
        # But wait, our view logic now tries to match the slug against slugified DB names.
        # So slugify(db_name) is the correct key.
        
        countries_map[group_key]['leagues'].append({
            'name': league.name,
            'slug': slugify(league.name),
            'url_slug': slugify(league.name)
        })
    
    # Sort alphabetically by Display Name
    sorted_countries = sorted(countries_map.values(), key=lambda x: x['name'])
    
    return {'sidebar_countries': sorted_countries}

