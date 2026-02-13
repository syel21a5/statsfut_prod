from .models import League
from django.utils.text import slugify
from matches.utils import COUNTRY_TRANSLATIONS

def sidebar_context(request):
    """
    Context processor to provide dynamic sidebar data (Leagues grouped by Country).
    """
    leagues = League.objects.all().order_by('country', 'name')
    
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

def get_flag_code(country_name):
    """
    Helper to map country names to Flag Icons (fi fi-xx).
    """
    country_lower = country_name.lower()
    
    # Map common names to ISO codes or 'fi' codes
    mapping = {
        'england': 'gb-eng',
        'uk': 'gb',
        'united kingdom': 'gb',
        'spain': 'es',
        'brazil': 'br',
        'brasil': 'br',
        'italy': 'it',
        'germany': 'de',
        'france': 'fr',
        'portugal': 'pt',
        'netherlands': 'nl',
        'holland': 'nl',
        'belgium': 'be',
        'argentina': 'ar',
        'usa': 'us',
        'united states': 'us',
        'turkey': 'tr',
        'russia': 'ru',
        'ukraine': 'ua',
        'sweden': 'se',
        'norway': 'no',
        'denmark': 'dk',
        'finland': 'fi',
        'austria': 'at',
        'switzerland': 'ch',
        'czech republic': 'cz',
        'czechia': 'cz',
        'poland': 'pl',
        'greece': 'gr',
        'scotland': 'gb-sct',
        'wales': 'gb-wls',
        'ireland': 'ie',
        'colombia': 'co',
        'chile': 'cl',
        'mexico': 'mx',
        'uruguay': 'uy',
        'japan': 'jp',
        'south korea': 'kr',
        'china': 'cn',
        'australia': 'au',
        # Add Portuguese names just in case
        'inglaterra': 'gb-eng',
        'espanha': 'es',
        'italia': 'it',
        'alemanha': 'de',
        'franca': 'fr',
        'frança': 'fr',
        'holanda': 'nl',
        'belgica': 'be',
        'bélgica': 'be',
        'estados unidos': 'us',
        'turquia': 'tr',
        'russia': 'ru',
        'ucrania': 'ua',
        'ucrânia': 'ua',
        'suecia': 'se',
        'suécia': 'se',
        'noruega': 'no',
        'dinamarca': 'dk',
        'finlandia': 'fi',
        'finlândia': 'fi',
        'grecia': 'gr',
        'grécia': 'gr',
        'japao': 'jp',
        'japão': 'jp',
    }
    
    return mapping.get(country_lower, 'xx') # 'xx' as generic/unknown
