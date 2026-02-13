from .models import League
from django.utils.text import slugify

def sidebar_context(request):
    """
    Context processor to provide dynamic sidebar data (Leagues grouped by Country).
    """
    leagues = League.objects.all().order_by('country', 'name')
    
    # Group by Country
    countries_map = {}
    for league in leagues:
        country_name = league.country
        if country_name not in countries_map:
            countries_map[country_name] = {
                'name': country_name,
                'slug': slugify(country_name),
                'leagues': [],
                'flag_code': get_flag_code(country_name)
            }
        
        countries_map[country_name]['leagues'].append({
            'name': league.name,
            'slug': slugify(league.name),
            'url_slug': slugify(league.name) # Use slugify for URL
        })
    
    # Sort countries? Or keep specific order?
    # For now, sort alphabetically, or maybe prioritize major ones if needed.
    # Let's just sort by name for now.
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
