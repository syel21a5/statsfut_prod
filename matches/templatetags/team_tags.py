from django import template
from django.contrib.staticfiles.finders import find

register = template.Library()

@register.simple_tag
def get_team_logo(team):
    """
    Returns the static URL for a team's logo if it exists locally,
    otherwise returns an empty string or a default placeholder.
    """
    if not team or not hasattr(team, 'api_id') or not team.api_id.startswith('sofa_'):
        return ''
        
    try:
        from django.utils.text import slugify
        country_slug = slugify(team.league.country)
        league_slug = slugify(team.league.name)
        
        # Determine the relative path inside static folder
        static_path = f'teams/{country_slug}/{league_slug}/{team.api_id}.png'
        
        # Check if file actually exists on disk using Django's static finders
        absolute_path = find(static_path)
        
        if absolute_path:
            # If it exists, return the static URL
            from django.templatetags.static import static
            return static(static_path)
    except Exception:
        pass
        
    return ''
