import sys

new_en = '''
translations_en = {
    'Sobre o': 'About',
    'O %(team_name)s é um clube de futebol profissional disputando a %(league_name)s em %(country)s.': 'The %(team_name)s is a professional football club competing in the %(league_name)s in %(country)s.',
    'Na temporada atual, a equipe ocupa a <strong>%(pos)sª</strong> posição na tabela de classificação, somando um total de <strong>%(pts)s</strong> pontos.': 'In the current season, the team occupies the <strong>%(pos)s</strong> position in the league table, summing up a total of <strong>%(pts)s</strong> points.',
    'No StatsFut, você acompanha os placares ao vivo do %(team_name)s, resultados detalhados, estatísticas de posse de bola, gols, cartões, escanteios, escalações e o calendário completo da temporada.': 'On StatsFut, you can follow live scores of %(team_name)s, detailed results, ball possession statistics, goals, cards, corners, lineups, and the full season schedule.',
    'Desempenho Geral': 'Overall Performance',
    'Média de <strong>%(avg_gf)s</strong> gols marcados e <strong>%(avg_ga)s</strong> sofridos por partida.': 'Average of <strong>%(avg_gf)s</strong> goals scored and <strong>%(avg_ga)s</strong> conceded per match.',
    'Ambas as equipes marcaram (BTTS) em <strong>%(btts)s%%</strong> dos jogos do clube.': 'Both teams scored (BTTS) in <strong>%(btts)s%%</strong> of the club\\'s matches.',
    'O artilheiro do elenco nesta temporada é <strong>%(name)s</strong> com <strong>%(goals)s</strong> gols marcados.': 'The team\\'s top scorer this season is <strong>%(name)s</strong> with <strong>%(goals)s</strong> goals scored.',
    'Placares ao vivo, jogadores, programação da temporada e resultados de hoje do <strong>%(team_name)s</strong> estão disponíveis no StatsFut.': 'Live scores, players, season schedule, and today\\'s results for <strong>%(team_name)s</strong> are available on StatsFut.',
    'Próxima partida do': 'Next match of',
    'O %(team_name)s jogará a próxima partida contra o <strong>%(opp)s</strong> no dia <strong>%(date)s</strong> pela <strong>%(league)s</strong>.': '%(team_name)s will play the next match against <strong>%(opp)s</strong> on <strong>%(date)s</strong> in <strong>%(league)s</strong>.',
    'Partida anterior do': 'Previous match of',
    'O jogo anterior do %(team_name)s foi contra o <strong>%(opp)s</strong> pela <strong>%(league)s</strong>, terminando com o placar de <strong>%(score)s</strong>.': 'The previous match of %(team_name)s was against <strong>%(opp)s</strong> in <strong>%(league)s</strong>, ending with a score of <strong>%(score)s</strong>.',
    'O <strong>%(team_name)s</strong> saiu vencedor desse confronto.': '<strong>%(team_name)s</strong> came out victorious in this clash.',
    'A equipe acabou sendo derrotada.': 'The team ended up being defeated.',
    'A partida terminou empatada.': 'The match ended in a draw.',
    'Gráfico de desempenho e forma': 'Performance and form chart',
    'O gráfico de desempenho e forma do <strong>%(team_name)s</strong> é um algoritmo exclusivo do StatsFut que geramos a partir das últimas partidas, estatísticas de gols, finalizações e escanteios. Ele ajuda a entender a tendência atual da equipe e a projetar os próximos confrontos.': 'The performance and form chart of <strong>%(team_name)s</strong> is an exclusive StatsFut algorithm that we generate from recent matches, goal statistics, shots, and corners. It helps to understand the team\\'s current trend and project upcoming clashes.',
    'Jogadores atuais do': 'Current players of',
    'Elenco': 'Squad',
    'anos': 'years'
}
'''

new_es_append = '''
    ,'Sobre o': 'Sobre el',
    'O %(team_name)s é um clube de futebol profissional disputando a %(league_name)s em %(country)s.': 'El %(team_name)s es un club de fútbol profesional que compite en la %(league_name)s de %(country)s.',
    'Na temporada atual, a equipe ocupa a <strong>%(pos)sª</strong> posição na tabela de classificação, somando um total de <strong>%(pts)s</strong> pontos.': 'En la temporada actual, el equipo ocupa la posición <strong>%(pos)s</strong> en la tabla de clasificación, sumando un total de <strong>%(pts)s</strong> puntos.',
    'No StatsFut, você acompanha os placares ao vivo do %(team_name)s, resultados detalhados, estatísticas de posse de bola, gols, cartões, escanteios, escalações e o calendário completo da temporada.': 'En StatsFut, puedes seguir los marcadores en vivo de %(team_name)s, resultados detallados, estadísticas de posesión de balón, goles, tarjetas, córners, alineaciones y el calendario completo de la temporada.',
    'Desempenho Geral': 'Rendimiento General',
    'Média de <strong>%(avg_gf)s</strong> gols marcados e <strong>%(avg_ga)s</strong> sofridos por partida.': 'Promedio de <strong>%(avg_gf)s</strong> goles marcados y <strong>%(avg_ga)s</strong> recibidos por partido.',
    'Ambas as equipes marcaram (BTTS) em <strong>%(btts)s%%</strong> dos jogos do clube.': 'Ambos equipos marcaron (BTTS) en el <strong>%(btts)s%%</strong> de los partidos del club.',
    'O artilheiro do elenco nesta temporada é <strong>%(name)s</strong> com <strong>%(goals)s</strong> gols marcados.': 'El máximo goleador del equipo esta temporada es <strong>%(name)s</strong> con <strong>%(goals)s</strong> goles marcados.',
    'Placares ao vivo, jogadores, programação da temporada e resultados de hoje do <strong>%(team_name)s</strong> estão disponíveis no StatsFut.': 'Marcadores en vivo, jugadores, calendario de la temporada y resultados de hoy de <strong>%(team_name)s</strong> están disponibles en StatsFut.',
    'Próxima partida do': 'Próximo partido del',
    'O %(team_name)s jogará a próxima partida contra o <strong>%(opp)s</strong> no dia <strong>%(date)s</strong> pela <strong>%(league)s</strong>.': 'El %(team_name)s jugará el próximo partido contra el <strong>%(opp)s</strong> el <strong>%(date)s</strong> en la <strong>%(league)s</strong>.',
    'Partida anterior do': 'Partido anterior del',
    'O jogo anterior do %(team_name)s foi contra o <strong>%(opp)s</strong> pela <strong>%(league)s</strong>, terminando com o placar de <strong>%(score)s</strong>.': 'El partido anterior del %(team_name)s fue contra el <strong>%(opp)s</strong> en la <strong>%(league)s</strong>, terminando con el marcador de <strong>%(score)s</strong>.',
    'O <strong>%(team_name)s</strong> saiu vencedor desse confronto.': 'El <strong>%(team_name)s</strong> salió victorioso en este encuentro.',
    'A equipe acabou sendo derrotada.': 'El equipo acabó siendo derrotado.',
    'A partida terminou empatada.': 'El partido terminó en empate.',
    'Gráfico de desempenho e forma': 'Gráfico de rendimiento y forma',
    'O gráfico de desempenho e forma do <strong>%(team_name)s</strong> é um algoritmo exclusivo do StatsFut que geramos a partir das últimas partidas, estatísticas de gols, finalizações e escanteios. Ele ajuda a entender a tendência atual da equipe e a projetar os próximos confrontos.': 'El gráfico de rendimiento y forma de <strong>%(team_name)s</strong> es un algoritmo exclusivo de StatsFut que generamos a partir de los últimos partidos, estadísticas de goles, tiros y córners. Ayuda a entender la tendencia actual del equipo y a proyectar próximos encuentros.',
    'Jogadores atuais do': 'Jugadores actuales del',
    'Elenco': 'Plantilla',
    'anos': 'años'
'''

new_de_append = '''
    ,'Sobre o': 'Über',
    'O %(team_name)s é um clube de futebol profissional disputando a %(league_name)s em %(country)s.': 'Der %(team_name)s ist ein professioneller Fußballverein, der in der %(league_name)s in %(country)s spielt.',
    'Na temporada atual, a equipe ocupa a <strong>%(pos)sª</strong> posição na tabela de classificação, somando um total de <strong>%(pts)s</strong> pontos.': 'In der aktuellen Saison belegt das Team den <strong>%(pos)s.</strong> Platz in der Tabelle und hat insgesamt <strong>%(pts)s</strong> Punkte gesammelt.',
    'No StatsFut, você acompanha os placares ao vivo do %(team_name)s, resultados detalhados, estatísticas de posse de bola, gols, cartões, escanteios, escalações e o calendário completo da temporada.': 'Auf StatsFut können Sie Live-Ergebnisse von %(team_name)s, detaillierte Ergebnisse, Ballbesitzstatistiken, Tore, Karten, Ecken, Aufstellungen und den kompletten Saisonplan verfolgen.',
    'Desempenho Geral': 'Allgemeine Leistung',
    'Média de <strong>%(avg_gf)s</strong> gols marcados e <strong>%(avg_ga)s</strong> sofridos por partida.': 'Durchschnittlich <strong>%(avg_gf)s</strong> erzielte Tore und <strong>%(avg_ga)s</strong> Gegentore pro Spiel.',
    'Ambas as equipes marcaram (BTTS) em <strong>%(btts)s%%</strong> dos jogos do clube.': 'Beide Teams trafen (BTTS) in <strong>%(btts)s%%</strong> der Spiele des Vereins.',
    'O artilheiro do elenco nesta temporada é <strong>%(name)s</strong> com <strong>%(goals)s</strong> gols marcados.': 'Der beste Torschütze des Teams in dieser Saison ist <strong>%(name)s</strong> mit <strong>%(goals)s</strong> erzielten Toren.',
    'Placares ao vivo, jogadores, programação da temporada e resultados de hoje do <strong>%(team_name)s</strong> estão disponíveis no StatsFut.': 'Live-Ergebnisse, Spieler, Saisonplan und die heutigen Ergebnisse von <strong>%(team_name)s</strong> sind auf StatsFut verfügbar.',
    'Próxima partida do': 'Nächstes Spiel von',
    'O %(team_name)s jogará a próxima partida contra o <strong>%(opp)s</strong> no dia <strong>%(date)s</strong> pela <strong>%(league)s</strong>.': 'Der %(team_name)s spielt das nächste Spiel gegen den <strong>%(opp)s</strong> am <strong>%(date)s</strong> in der <strong>%(league)s</strong>.',
    'Partida anterior do': 'Vorheriges Spiel von',
    'O jogo anterior do %(team_name)s foi contra o <strong>%(opp)s</strong> pela <strong>%(league)s</strong>, terminando com o placar de <strong>%(score)s</strong>.': 'Das vorherige Spiel von %(team_name)s war gegen den <strong>%(opp)s</strong> in der <strong>%(league)s</strong> und endete mit dem Ergebnis <strong>%(score)s</strong>.',
    'O <strong>%(team_name)s</strong> saiu vencedor desse confronto.': 'Der <strong>%(team_name)s</strong> ging als Sieger aus dieser Begegnung hervor.',
    'A equipe acabou sendo derrotada.': 'Das Team wurde besiegt.',
    'A partida terminou empatada.': 'Das Spiel endete unentschieden.',
    'Gráfico de desempenho e forma': 'Leistungs- und Formdiagramm',
    'O gráfico de desempenho e forma do <strong>%(team_name)s</strong> é um algoritmo exclusivo do StatsFut que geramos a partir das últimas partidas, estatísticas de gols, finalizações e escanteios. Ele ajuda a entender a tendência atual da equipe e a projetar os próximos confrontos.': 'Das Leistungs- und Formdiagramm von <strong>%(team_name)s</strong> ist ein exklusiver StatsFut-Algorithmus, den wir aus aktuellen Spielen, Torstatistiken, Schüssen und Ecken generieren. Es hilft, den aktuellen Trend des Teams zu verstehen und anstehende Begegnungen zu projizieren.',
    'Jogadores atuais do': 'Aktuelle Spieler von',
    'Elenco': 'Kader',
    'anos': 'Jahre'
'''

with open('translate_po.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'translations_en = {' not in content:
    content = content.replace('translations_es = {', new_en + '\n\ntranslations_es = {')

anchor_es = "futebol mundial com dados precisos.'\n}"
if new_es_append not in content:
    content = content.replace(anchor_es, "futebol mundial com dados precisos.'" + new_es_append + "\n}")

anchor_de = "präzisen Daten zu verfolgen.'\n}"
if new_de_append not in content:
    content = content.replace(anchor_de, "präzisen Daten zu verfolgen.'" + new_de_append + "\n}")

process_en = "fix_and_translate_po('locale/en/LC_MESSAGES/django.po', translations_en)"
if process_en not in content:
    content += f"\n{process_en}\n"

with open('translate_po.py', 'w', encoding='utf-8') as f:
    f.write(content)
