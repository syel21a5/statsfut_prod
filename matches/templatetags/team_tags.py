from django import template  # type: ignore

register = template.Library()

@register.simple_tag
def get_team_logo(team):
    """
    Globally disabled. Returns empty string to avoid rendering logos.
    """
    return ''
