import os

po_path = 'locale/pt_BR/LC_MESSAGES/django.po'

additions = """
msgid "Detailed goals statistics separated by Full Time (FT), Half Time (HT) and Second Half (2H) for the <strong>%(league_name)s</strong>. Discover the average goals scored and conceded in each stage of the match, as well as the percentages for over 0.5, 1.5, and 2.5 goals per half. Use these insights to find value in HT and 2H markets."
msgstr "Estatísticas detalhadas de gols separados por Partida Completa (FT), Primeiro Tempo (HT) e Segundo Tempo (2H) para o(a) <strong>%(league_name)s</strong>. Descubra as médias de gols marcados e sofridos em cada etapa do jogo, além das porcentagens de Mais de 0.5, 1.5 e 2.5 gols por tempo. Use esses dados para encontrar valor nos mercados de HT e 2H."

msgid "Focused analysis on the Both Teams to Score (BTTS) market in the <strong>%(league_name)s</strong>. See how often teams score and concede in the same match, whether playing at home, away, or across all matches in the season. Identify the teams with the highest BTTS trends for your sports predictions."
msgstr "Análise focada no mercado de Ambas as Equipes Marcam (BTTS) no(a) <strong>%(league_name)s</strong>. Veja a frequência com que as equipes marcam e sofrem gols no mesmo jogo, seja jogando em casa, fora, ou no geral da temporada. Identifique os times com as maiores tendências de BTTS para embasar seus palpites esportivos."

msgid "Defensive statistics and Clean Sheets market for the <strong>%(league_name)s</strong>. Find out which teams have the most solid defenses, the highest probability of not conceding goals in their matches, and the percentage of games they win to nil (Win To Nil). Essential data for defensive performance analysis."
msgstr "Estatísticas defensivas e mercado de Clean Sheets (Jogos Sem Sofrer Gols) no(a) <strong>%(league_name)s</strong>. Descubra quais equipes possuem as defesas mais sólidas, a maior probabilidade de não serem vazadas em seus confrontos, e a porcentagem de jogos que vencem sem sofrer gols (Win To Nil). Dados essenciais para análise de desempenho defensivo."

msgid "Advanced statistics on Goal Timings in the <strong>%(league_name)s</strong>. Understand in which 15-minute segments teams score or concede the most goals, which teams usually score the First Goal of the match, their performance when leading at half-time, and the most common Half Time / Full Time (HT/FT) outcomes."
msgstr "Estatísticas avançadas sobre o Tempo dos Gols (Goal Timings) no(a) <strong>%(league_name)s</strong>. Entenda em quais segmentos de 15 minutos as equipes mais marcam ou sofrem gols, quais times costumam marcar o Primeiro Gol da partida, o desempenho quando estão liderando no intervalo, e os resultados mais comuns de Intervalo/Final (HT/FT)."
"""

with open(po_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Only append if not already there
if "Detailed goals statistics separated by Full Time" not in content:
    with open(po_path, 'a', encoding='utf-8') as f:
        f.write("\n" + additions + "\n")
    print("Translations appended.")
else:
    print("Translations already exist.")
