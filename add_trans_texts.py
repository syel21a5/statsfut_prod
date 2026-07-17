import os

file_path = 'locale/pt_BR/LC_MESSAGES/django.po'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

t1 = 'msgid "Distribution of goals scored across 15-minute periods of the match."'
t1_res = 'msgstr "Distribuição dos gols marcados em períodos de 15 minutos da partida."'

t2 = 'msgid "Ranking of teams with the highest number of Goals For (GF) in the league."'
t2_res = 'msgstr "Ranking das equipes com o maior número de Gols Marcados (GF) na liga."'

if t1 not in content:
    content += f'\n\n{t1}\n{t1_res}\n'
else:
    content = content.replace(f'{t1}\nmsgstr ""', f'{t1}\n{t1_res}')

if t2 not in content:
    content += f'\n\n{t2}\n{t2_res}\n'
else:
    content = content.replace(f'{t2}\nmsgstr ""', f'{t2}\n{t2_res}')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
