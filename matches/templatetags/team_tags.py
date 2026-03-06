from django import template

register = template.Library()

@register.simple_tag
def get_team_logo(team):
    """
    Returns the static URL for a team's logo.
    Works in both development and production.
    If the image file doesn't exist, the browser silently ignores it.
    """
    if not team or getattr(team, 'api_id', None) is None or not team.api_id.startswith('sofa_'):
        return ''

    try:
        from django.utils.text import slugify
        from django.templatetags.static import static

        country_slug = slugify(team.league.country)
        league_slug = slugify(team.league.name)
        static_path = f'teams/{country_slug}/{league_slug}/{team.api_id}.png'

        return static(static_path)

    except Exception:
        pass

    return ''
