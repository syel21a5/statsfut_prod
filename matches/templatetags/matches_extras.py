from django import template

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


COUNTRY_EN_MAP = {
    "Inglaterra": "England",
    "Brasil": "Brazil",
    "Espanha": "Spain",
    "Alemanha": "Germany",
    "Itália": "Italy",
    "França": "France",
    "Portugal": "Portugal",
}


@register.filter
def country_en(value):
    if not value:
        return ""
    return COUNTRY_EN_MAP.get(str(value), value)

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
