from django import template

register = template.Library()

COUNTRY_CODES = {
    'England': 'gb-eng',
    'Belgium': 'be',
    'Germany': 'de',
    'Brazil': 'br',
    'Spain': 'es',
    'Sweden': 'se',
    'Norway': 'no',
    'France': 'fr',
    'Italy': 'it',
    'Netherlands': 'nl',
    'Japan': 'jp',
    'Ukraine': 'ua',
    'Poland': 'pl',
    'Ghana': 'gh',
    'Portugal': 'pt',
    'Argentina': 'ar',
    'USA': 'us',
    'Switzerland': 'ch',
    'Egypt': 'eg',
    'Scotland': 'gb-sct',
    'Wales': 'gb-wls',
    'Ireland': 'ie',
    'Northern Ireland': 'gb-nir',
    'Austria': 'at',
    'Australia': 'au',
    'Czech': 'cz',
    'Denmark': 'dk',
    'Finland': 'fi',
    'Greece': 'gr',
    'Russia': 'ru',
    'Turkey': 'tr',
    # Add more as needed
}

@register.filter
def get_flag_url(country_name):
    """
    Returns the flagcdn URL for a given country name.
    Uses w20 (width 20) for small icons.
    """
    if not country_name:
        return ""
    
    code = COUNTRY_CODES.get(country_name)
    if not code:
        # Fallback for unknown countries or try lowercasing 2-letter codes if consistent
        return ""
        
    return f"https://flagcdn.com/w20/{code}.png"
