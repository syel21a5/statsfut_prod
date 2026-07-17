import os

file_path = 'locale/pt_BR/LC_MESSAGES/django.po'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix Win
content = content.replace('msgid "Win"\nmsgstr ""', 'msgid "Win"\nmsgstr "Vitória"')

# Fix Draw
content = content.replace('msgid "Draw"\nmsgstr ""', 'msgid "Draw"\nmsgstr "Empate"')

# Fix Defeat
content = content.replace('msgid "Defeat"\nmsgstr ""', 'msgid "Defeat"\nmsgstr "Derrota"')

# Fix Over 2.5 Goals
content = content.replace('msgid "Over 2.5 Goals"\nmsgstr ""', 'msgid "Over 2.5 Goals"\nmsgstr "Mais de 2.5 Gols"')

# Fix Clean Sheet
content = content.replace('msgid "Clean Sheet"\nmsgstr ""', 'msgid "Clean Sheet"\nmsgstr "Clean Sheet (Não Sofreu Gols)"')

# Fix Failed to Score
content = content.replace('msgid "Failed to Score"\nmsgstr ""', 'msgid "Failed to Score"\nmsgstr "Não Marcou (FTS)"')

# Fix Half-Time Score
content = content.replace('msgid "Half-Time Score"\nmsgstr ""', 'msgid "Half-Time Score"\nmsgstr "Placar no Intervalo"')

# Fix Recent matches. CS: Clean Sheet (did not concede), FTS: Failed To Score, HT: Half-Time score.
content = content.replace('msgid "Recent matches. CS: Clean Sheet (did not concede), FTS: Failed To Score, HT: Half-Time score."\nmsgstr ""', 'msgid "Recent matches. CS: Clean Sheet (did not concede), FTS: Failed To Score, HT: Half-Time score."\nmsgstr "Partidas recentes. CS: Clean Sheet (Não sofreu gols), FTS: Failed To Score (Não marcou), HT: Placar no intervalo."')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
