import re

with open('locale/pt_BR/LC_MESSAGES/django.po', 'r', encoding='utf-8') as f:
    content = f.read()

new_translations = [
    ('Corners Performance Ranking', 'Ranking de Escanteios'),
    ('Cards & Discipline Ranking', 'Ranking de Cartões e Disciplina'),
    ('Shots per Match', 'Finalizações por Partida'),
    ('Goal Minutes Distribution', 'Distribuição de Gols por Minuto'),
    ('Ranking of teams with the most corners on average per match (For, Against and Total).', 'Ranking das equipes com mais escanteios em média por partida (A Favor, Contra e Total).'),
    ('Disciplinary ranking showing the teams with the most yellow and red cards per match.', 'Ranking disciplinar mostrando as equipes com mais cartões amarelos e vermelhos por partida.'),
    ('Ranking of teams with the highest average number of shots per match.', 'Ranking das equipes com a maior média de finalizações por partida.'),
    ('Distribution of goals scored across 15-minute periods of the match.', 'Distribuição de gols marcados ao longo de períodos de 15 minutos da partida.'),
    ('League top scorers for the current season, including penalty goals.', 'Artilheiros da liga para a temporada atual, incluindo gols de pênalti.')
]

with open('locale/pt_BR/LC_MESSAGES/django.po', 'a', encoding='utf-8') as f:
    for msgid, msgstr in new_translations:
        if f'msgid "{msgid}"' not in content:
            f.write(f'\n\nmsgid "{msgid}"\nmsgstr "{msgstr}"\n')
