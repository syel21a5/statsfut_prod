from django import template
from matches.utils import COUNTRY_TRANSLATIONS

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return ""
    if hasattr(dictionary, "get"):
        return dictionary.get(key)
    try:
        return dictionary[key]
    except Exception:
        return ""

@register.filter
def get_key_pct(dictionary, key):
    """
    Tries to get dictionary[key + '_pct'].
    """
    if not dictionary:
        return 0
    # Try direct key
    val = dictionary.get(key)
    # If key is constructing a pct key
    pct_key = f"{key}_pct"
    if pct_key in dictionary:
        return dictionary[pct_key]
    return val

@register.filter
def split(value, arg):
    return value.split(arg)


@register.filter
def country_en(value):
    if not value:
        return ""
    return COUNTRY_TRANSLATIONS.get(str(value), value)

@register.filter
def is_team(team, target):
    return team == target

@register.filter
def probability_label(val1, val2):
    try:
        avg = (float(val1) + float(val2)) / 2
        if avg >= 65: return "High"
        if avg >= 40: return "Medium"
        return "Low"
    except (ValueError, TypeError):
        return "-"
@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def fair_odd(value):
    """
    Converte uma probabilidade em % (ex: 67) para Odd Justa (ex: 1.49).
    Fórmula: 100 / probabilidade. Retorna string formatada com 2 casas decimais.
    """
    try:
        val = float(value)
        if val <= 0:
            return "-"
        odd = 100.0 / val
        return f"{odd:.2f}"
    except (ValueError, TypeError):
        return "-"

from django.urls import translate_url

@register.simple_tag(takes_context=True)
def translated_url(context, language):
    request = context.get('request')
    if not request:
        return ''
    return translate_url(request.path, language)
