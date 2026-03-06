from django import template
import os

register = template.Library()

@register.simple_tag
def get_team_logo(team):
    """
    Returns the static URL for a team's logo if it exists locally,
    otherwise returns an empty string.
    Works both in development (DEBUG=True) and production (DEBUG=False).
    """
    if not team or getattr(team, 'api_id', None) is None or not team.api_id.startswith('sofa_'):
        return ''

    try:
        from django.utils.text import slugify
        from django.conf import settings
        from django.templatetags.static import static

        country_slug = slugify(team.league.country)
        league_slug = slugify(team.league.name)
        static_path = f'teams/{country_slug}/{league_slug}/{team.api_id}.png'

        # PRODUCTION: Check in STATIC_ROOT (where collectstatic puts files)
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if static_root:
            # Normalize path so os.path.join works even if static_path has forward slashes
            normalized_static_path = os.path.normpath(static_path)
            full_path = os.path.join(static_root, normalized_static_path)
            if os.path.exists(full_path):
                return static(static_path)

        # DEVELOPMENT: Check using Django's static finders (only works with DEBUG=True)
        from django.contrib.staticfiles.finders import find
        absolute_path = find(static_path)
        if absolute_path:
            return static(static_path)

    except Exception:
        pass

    return ''
