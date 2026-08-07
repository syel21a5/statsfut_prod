import os
import re

strings = {
    'Golden Double HT (1st Half Goals)': {
        'pt': 'Dupla Ouro HT (Gols no 1º Tempo)',
        'es': 'Doble de Oro HT (Goles en la 1ª Mitad)',
        'de': 'Goldenes Doppel HT (Tore in der 1. Halbzeit)',
    },
    'FT Goals Double (Over 1.5 Goals)': {
        'pt': 'Dupla de Gols FT (Mais de 1.5 Gols)',
        'es': 'Doble de Goles FT (Más de 1.5 Goles)',
        'de': 'Tore Doppel FT (Über 1.5 Tore)',
    },
    'Corners Double (Over 9.5 Corners)': {
        'pt': 'Dupla de Cantos (Over 9.5 Escanteios)',
        'es': 'Doble de Córners (Más de 9.5 Córners)',
        'de': 'Ecken Doppel (Über 9.5 Ecken)',
    },
    'BTTS Double (Goals on Both Sides)': {
        'pt': 'Dupla Ambas Marcam (Gols dos Dois Lados)',
        'es': 'Doble Ambos Marcan (Goles de Ambos Lados)',
        'de': 'BTTS Doppel (Tore auf beiden Seiten)',
    },
    'Favorites Double (Clear Wins)': {
        'pt': 'Dupla de Favoritos (Vitórias Claras)',
        'es': 'Doble de Favoritos (Victorias Claras)',
        'de': 'Favoriten Doppel (Klare Siege)',
    },
    'Under Control Double (Under 3.5 Goals)': {
        'pt': 'Dupla Sob Controle (Menos de 3.5 Gols)',
        'es': 'Doble Bajo Control (Menos de 3.5 Goles)',
        'de': 'Unter Kontrolle Doppel (Unter 3.5 Tore)',
    },
    'Iron Defense Double (BTTS No)': {
        'pt': 'Dupla Defesa de Ferro (Ambas Marcam Não)',
        'es': 'Doble Defensa de Hierro (Ambos Marcan No)',
        'de': 'Eiserne Verteidigung Doppel (BTTS Nein)',
    },
    'Double Chance Double (Extra Safety)': {
        'pt': 'Dupla Dupla Chance (Segurança Extra)',
        'es': 'Doble Doble Oportunidad (Seguridad Extra)',
        'de': 'Doppelte Chance Doppel (Zusätzliche Sicherheit)',
    },
    'FT Goals Treble (Over 1.5 Goals)': {
        'pt': 'Tripla de Gols FT (Mais de 1.5 Gols)',
        'es': 'Triple de Goles FT (Más de 1.5 Goles)',
        'de': 'Tore Dreier FT (Über 1.5 Tore)',
    },
    'Double Chance Treble (Maximum Safety)': {
        'pt': 'Tripla Dupla Chance (Segurança Máxima)',
        'es': 'Triple Doble Oportunidad (Máxima Seguridad)',
        'de': 'Doppelte Chance Dreier (Maximale Sicherheit)',
    },
    'Leverage Treble (Over 0.5 FT Goals)': {
        'pt': 'Tripla Alavancagem (Mais de 0.5 Gols FT)',
        'es': 'Triple Apalancamiento (Más de 0.5 Goles FT)',
        'de': 'Hebel Dreier (Über 0.5 Tore FT)',
    },
    'Golden Treble HT (1st Half Goals)': {
        'pt': 'Tripla Ouro HT (Gols no 1º Tempo)',
        'es': 'Triple de Oro HT (Goles en la 1ª Mitad)',
        'de': 'Goldenes Dreier HT (Tore in der 1. Halbzeit)',
    },
    'Golden Multiple (Safety & Value)': {
        'pt': 'Múltipla de Ouro (Segurança & Valor)',
        'es': 'Múltiple de Oro (Seguridad & Valor)',
        'de': 'Goldene Kombi (Sicherheit & Wert)',
    },
    'Super Leverage Multiple (Giant Odds)': {
        'pt': 'Super Múltipla Alavancagem (Odds Gigantes)',
        'es': 'Super Múltiple Apalancamiento (Cuotas Gigantes)',
        'de': 'Super Hebel Kombi (Riesige Quoten)',
    },
    'Trixie Combo: DC + Goal Range': {
        'pt': 'Trixie Combo: DC + Faixa de Gols',
        'es': 'Combo Trixie: DC + Rango de Goles',
        'de': 'Trixie Combo: DC + Torbereich',
    },
    'Trixie Combo: Goals + BTTS': {
        'pt': 'Trixie Combo: Gols + Ambas Marcam',
        'es': 'Combo Trixie: Goles + Ambos Marcan',
        'de': 'Trixie Combo: Tore + BTTS',
    },
    'Special Trixie: 2nd Half with Most Goals': {
        'pt': 'Trixie Especial: 2º Tempo com Mais Gols',
        'es': 'Trixie Especial: 2ª Mitad con Más Goles',
        'de': 'Spezial Trixie: 2. Halbzeit mit den meisten Toren',
    },
    'Pressure Trixie: Team Scores in 2nd Half': {
        'pt': 'Trixie Pressão: Equipe Marca no 2º Tempo',
        'es': 'Trixie Presión: Equipo Marca en 2ª Mitad',
        'de': 'Druck Trixie: Team trifft in der 2. Halbzeit',
    },
    'Goal in 1st Half': {
        'pt': 'Gol no 1º Tempo',
        'es': 'Gol en la 1ª Mitad',
        'de': 'Tor in der 1. Halbzeit',
    },
    'Over 1.5 FT Goals': {
        'pt': 'Mais de 1.5 Gols FT',
        'es': 'Más de 1.5 Goles FT',
        'de': 'Über 1.5 Tore FT',
    },
    'Both Teams to Score - Yes': {
        'pt': 'Ambas Marcam - Sim',
        'es': 'Ambos Marcan - Sí',
        'de': 'Beide Teams treffen - Ja',
    },
    'Both Teams to Score - No': {
        'pt': 'Ambas Marcam - Não',
        'es': 'Ambos Marcan - No',
        'de': 'Beide Teams treffen - Nein',
    },
    'Over 9.5 Corners': {
        'pt': 'Mais de 9.5 Escanteios',
        'es': 'Más de 9.5 Córners',
        'de': 'Über 9.5 Ecken',
    },
    'Over 0.5 FT Goals': {
        'pt': 'Mais de 0.5 Gols FT',
        'es': 'Más de 0.5 Goles FT',
        'de': 'Über 0.5 Tore FT',
    },
    'Under 3.5 FT Goals': {
        'pt': 'Menos de 3.5 Gols FT',
        'es': 'Menos de 3.5 Goles FT',
        'de': 'Unter 3.5 Tore FT',
    },
    'Group': {
        'pt': 'Grupo',
        'es': 'Grupo',
        'de': 'Gruppe',
    },
    'Hedge on Favorite': {
        'pt': 'Hedge ao Favorito',
        'es': 'Hedge al Favorito',
        'de': 'Hedge auf Favoriten',
    },
    'Win': {
        'pt': 'Vitória',
        'es': 'Victoria',
        'de': 'Sieg',
    },
    'or Draw': {
        'pt': 'ou Empate',
        'es': 'o Empate',
        'de': 'oder Unentschieden',
    },
    'Goals in Match': {
        'pt': 'Gols no Jogo',
        'es': 'Goles en el Partido',
        'de': 'Tore im Spiel',
    },
    'Draw or': {
        'pt': 'Empate ou',
        'es': 'Empate o',
        'de': 'Unentschieden oder',
    },
    '+2.5 Goals & BTTS Yes': {
        'pt': '+2.5 Gols & Ambas Sim',
        'es': '+2.5 Goles & Ambos Sí',
        'de': '+2.5 Tore & BTTS Ja',
    },
    '-2.5 Goals & BTTS No': {
        'pt': '-2.5 Gols & Ambas Não',
        'es': '-2.5 Goles & Ambos No',
        'de': '-2.5 Tore & BTTS Nein',
    },
    '2nd Half with Most Goals': {
        'pt': '2º Tempo Com Mais Gols',
        'es': '2ª Mitad con Más Goles',
        'de': '2. Halbzeit mit den meisten Toren',
    },
    'Scores in 2nd Half': {
        'pt': 'Marca no 2º Tempo',
        'es': 'Marca en la 2ª Mitad',
        'de': 'Trifft in der 2. Halbzeit',
    }
}

for lang in ['pt', 'pt_BR', 'es', 'de']:
    po_path = f"locale/{lang}/LC_MESSAGES/django.po"
    if not os.path.exists(po_path):
        continue
    
    with open(po_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    for msgid, translations in strings.items():
        lang_key = lang if lang != 'pt_BR' else 'pt'
        msgstr = translations.get(lang_key, '')
        
        # Look for msgid "..."\nmsgstr ""
        pattern = re.compile(rf'msgid "{re.escape(msgid)}"\nmsgstr ""')
        if pattern.search(content):
            content = pattern.sub(f'msgid "{msgid}"\nmsgstr "{msgstr}"', content)
        else:
            # If not found at all, append it
            if f'msgid "{msgid}"' not in content:
                content += f'\nmsgid "{msgid}"\nmsgstr "{msgstr}"\n'

    with open(po_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("PO files patched successfully via regex substitution.")
