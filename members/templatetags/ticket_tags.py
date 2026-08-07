import re
from django import template
from django.utils.translation import gettext as _

register = template.Library()

@register.filter
def translate_ticket(text):
    if not text:
        return text
        
    original = str(text)
    
    # Translating main strategy titles
    t = original.replace("Dupla Ouro HT (Gols no 1º Tempo)", str(_("Golden Double HT (1st Half Goals)")))
    t = t.replace("Dupla de Gols FT (Mais de 1.5 Gols)", str(_("FT Goals Double (Over 1.5 Goals)")))
    t = t.replace("Dupla de Cantos (Over 9.5 Escanteios)", str(_("Corners Double (Over 9.5 Corners)")))
    t = t.replace("Dupla Ambas Marcam (Gols dos Dois Lados)", str(_("BTTS Double (Goals on Both Sides)")))
    t = t.replace("Dupla de Favoritos (Vitórias Claras)", str(_("Favorites Double (Clear Wins)")))
    t = t.replace("Dupla Sob Controle (Menos de 3.5 Gols)", str(_("Under Control Double (Under 3.5 Goals)")))
    t = t.replace("Dupla Defesa de Ferro (Ambas Marcam Não)", str(_("Iron Defense Double (BTTS No)")))
    t = t.replace("Dupla Dupla Chance (Segurança Extra)", str(_("Double Chance Double (Extra Safety)")))
    
    t = t.replace("Tripla de Gols FT (Mais de 1.5 Gols)", str(_("FT Goals Treble (Over 1.5 Goals)")))
    t = t.replace("Tripla Dupla Chance (Segurança Máxima)", str(_("Double Chance Treble (Maximum Safety)")))
    t = t.replace("Tripla Alavancagem (Mais de 0.5 Gols FT)", str(_("Leverage Treble (Over 0.5 FT Goals)")))
    t = t.replace("Tripla Ouro HT (Gols no 1º Tempo)", str(_("Golden Treble HT (1st Half Goals)")))
    
    t = t.replace("Múltipla de Ouro (Segurança & Valor)", str(_("Golden Multiple (Safety & Value)")))
    t = t.replace("Super Múltipla Alavancagem (Odds Gigantes)", str(_("Super Leverage Multiple (Giant Odds)")))
    
    t = t.replace("Trixie Combo: DC + Faixa de Gols", str(_("Trixie Combo: DC + Goal Range")))
    t = t.replace("Trixie Combo: Gols + Ambas Marcam", str(_("Trixie Combo: Goals + BTTS")))
    t = t.replace("Trixie Especial: 2º Tempo com Mais Gols", str(_("Special Trixie: 2nd Half with Most Goals")))
    t = t.replace("Trixie Pressão: Equipe Marca no 2º Tempo", str(_("Pressure Trixie: Team Scores in 2nd Half")))
    
    # Common Groups
    t = re.sub(r' - Grupo ([A-Z])', lambda m: f" - {str(_('Group'))} {m.group(1)}", t)
    
    # Hedge
    t = t.replace("Hedge ao Favorito - ", str(_("Hedge on Favorite")) + " - ")
    
    # Selection Labels
    t = t.replace("Gol no 1º Tempo", str(_("Goal in 1st Half")))
    t = t.replace("Mais de 1.5 Gols FT", str(_("Over 1.5 FT Goals")))
    t = t.replace("Ambas Marcam - Sim", str(_("Both Teams to Score - Yes")))
    t = t.replace("Mais de 9.5 Escanteios", str(_("Over 9.5 Corners")))
    t = t.replace("Mais de 0.5 Gols FT", str(_("Over 0.5 FT Goals")))
    t = t.replace("Menos de 3.5 Gols FT", str(_("Under 3.5 FT Goals")))
    t = t.replace("Ambas Marcam - Não", str(_("Both Teams to Score - No")))
    
    # Dynamic labels with teams
    t = re.sub(r'^Vitória do (.*)', lambda m: f"{m.group(1)} {str(_('Win'))}", t)
    t = re.sub(r'^1X - (.*) ou Empate', lambda m: f"1X - {m.group(1)} {str(_('or Draw'))}", t)
    t = re.sub(r'^X2 - (.*) ou Empate', lambda m: f"X2 - {m.group(1)} {str(_('or Draw'))}", t)
    t = re.sub(r'^Hedge - Vitória do (.*)', lambda m: f"Hedge - {m.group(1)} {str(_('Win'))}", t)
    
    t = re.sub(r'(.*) ou Empate & 2-4 Gols no Jogo', lambda m: f"{m.group(1)} {str(_('or Draw'))} & 2-4 {str(_('Goals in Match'))}", t)
    t = t.replace("Empate ou ", str(_("Draw or")) + " ")
    
    t = t.replace("+2.5 Gols & Ambas Sim", str(_("+2.5 Goals & BTTS Yes")))
    t = t.replace("-2.5 Gols & Ambas Não", str(_("-2.5 Goals & BTTS No")))
    t = t.replace("2º Tempo Com Mais Gols", str(_("2nd Half with Most Goals")))
    
    t = re.sub(r'(.*) Marca no 2º Tempo', lambda m: f"{m.group(1)} {str(_('Scores in 2nd Half'))}", t)

    return t
