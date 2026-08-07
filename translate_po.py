import re
import os

# Dictionary of translations

translations_en = {
    'Sobre o': 'About',
    'O %(team_name)s é um clube de futebol profissional disputando a %(league_name)s em %(country)s.': 'The %(team_name)s is a professional football club competing in the %(league_name)s in %(country)s.',
    'Na temporada atual, a equipe ocupa a <strong>%(pos)sª</strong> posição na tabela de classificação, somando um total de <strong>%(pts)s</strong> pontos.': 'In the current season, the team occupies the <strong>%(pos)s</strong> position in the league table, summing up a total of <strong>%(pts)s</strong> points.',
    'No StatsFut, você acompanha os placares ao vivo do %(team_name)s, resultados detalhados, estatísticas de posse de bola, gols, cartões, escanteios, escalações e o calendário completo da temporada.': 'On StatsFut, you can follow live scores of %(team_name)s, detailed results, ball possession statistics, goals, cards, corners, lineups, and the full season schedule.',
    'Desempenho Geral': 'Overall Performance',
    'Média de <strong>%(avg_gf)s</strong> gols marcados e <strong>%(avg_ga)s</strong> sofridos por partida.': 'Average of <strong>%(avg_gf)s</strong> goals scored and <strong>%(avg_ga)s</strong> conceded per match.',
    'Ambas as equipes marcaram (BTTS) em <strong>%(btts)s%%</strong> dos jogos do clube.': 'Both teams scored (BTTS) in <strong>%(btts)s%%</strong> of the club\'s matches.',
    'O artilheiro do elenco nesta temporada é <strong>%(name)s</strong> com <strong>%(goals)s</strong> gols marcados.': 'The team\'s top scorer this season is <strong>%(name)s</strong> with <strong>%(goals)s</strong> goals scored.',
    'Placares ao vivo, jogadores, programação da temporada e resultados de hoje do <strong>%(team_name)s</strong> estão disponíveis no StatsFut.': 'Live scores, players, season schedule, and today\'s results for <strong>%(team_name)s</strong> are available on StatsFut.',
    'Próxima partida do': 'Next match of',
    'O %(team_name)s jogará a próxima partida contra o <strong>%(opp)s</strong> no dia <strong>%(date)s</strong> pela <strong>%(league)s</strong>.': '%(team_name)s will play the next match against <strong>%(opp)s</strong> on <strong>%(date)s</strong> in <strong>%(league)s</strong>.',
    'Partida anterior do': 'Previous match of',
    'O jogo anterior do %(team_name)s foi contra o <strong>%(opp)s</strong> pela <strong>%(league)s</strong>, terminando com o placar de <strong>%(score)s</strong>.': 'The previous match of %(team_name)s was against <strong>%(opp)s</strong> in <strong>%(league)s</strong>, ending with a score of <strong>%(score)s</strong>.',
    'O <strong>%(team_name)s</strong> saiu vencedor desse confronto.': '<strong>%(team_name)s</strong> came out victorious in this clash.',
    'A equipe acabou sendo derrotada.': 'The team ended up being defeated.',
    'A partida terminou empatada.': 'The match ended in a draw.',
    'Gráfico de desempenho e forma': 'Performance and form chart',
    'O gráfico de desempenho e forma do <strong>%(team_name)s</strong> é um algoritmo exclusivo do StatsFut que geramos a partir das últimas partidas, estatísticas de gols, finalizações e escanteios. Ele ajuda a entender a tendência atual da equipe e a projetar os próximos confrontos.': 'The performance and form chart of <strong>%(team_name)s</strong> is an exclusive StatsFut algorithm that we generate from recent matches, goal statistics, shots, and corners. It helps to understand the team\'s current trend and project upcoming clashes.',
    'Jogadores atuais do': 'Current players of',
    'Elenco': 'Squad',
    'anos': 'years'
    ,'Estatísticas completas e previsões detalhadas para a partida entre': 'Complete statistics and detailed predictions for the match between'
    ,'e': 'and'
    ,'válida pela': 'valid for the'
    ,'Analise as probabilidades de Ambas Marcam (BTTS), Mais de 2.5 Gols, cantos, cartões e histórico de confrontos diretos (H2H) para apoiar suas análises e palpites esportivos baseados em dados.': 'Analyze the probabilities of Both Teams to Score (BTTS), Over 2.5 Goals, corners, cards, and head-to-head (H2H) history to support your data-driven sports analysis and predictions.'
    ,'Gols & Tempos': 'Goals & Halves'
    ,'Escanteios': 'Corners'
    ,'Cartões': 'Cards'
    ,'Chutes': 'Shots'
    ,'Especiais & Combos': 'Specials & Combos'
    ,'Ambas Marcam Detalhado': 'Both Teams to Score Detailed'
    ,'Faixa de Gols (Partida)': 'Goal Range (Match)'
    ,'Faixa (1º Tempo)': 'Range (1st Half)'
    ,'Faixa (2º Tempo)': 'Range (2nd Half)'
    ,'Margem de Vitória Exata': 'Exact Winning Margin'
    ,'por 1 gol': 'by 1 goal'
    ,'por 2 gols': 'by 2 goals'
    ,'por 3+ gols': 'by 3+ goals'
    ,'Empate com gols': 'Score Draw'
    ,'Empate sem gols (0-0)': 'Goalless Draw (0-0)'
    ,'Metades & Tempos': 'Halves & Periods'
    ,'Mais gols no 1º Tempo': 'More goals in 1st Half'
    ,'Mais gols no 2º Tempo': 'More goals in 2nd Half'
    ,'Metades com gols iguais': 'Equal goals in both halves'
    ,'Marcar em Ambos os Tempos': 'To Score in Both Halves'
    ,'Marcar Ambos Tempos': 'To Score Both Halves'
    ,'Marcar pelo menos Um': 'To Score At Least One'
    ,'Intervalo / Fim do Jogo': 'Half-Time / Full-Time'
    ,'Resultado 1º Tempo': '1st Half Result'
    ,'Vence HT': 'Wins HT'
    ,'Empate HT': 'Draw HT'
    ,'Vencedor + Ambos Marcam': 'Winner + BTTS'
    ,'Sim': 'Yes'
    ,'Empate': 'Draw'
    ,'Chance Dupla + Faixa de Gols': 'Double Chance + Goal Range'
    ,'Gols': 'Goals'
    ,'Handicap Asiático & Europeu': 'Asian & European Handicap'
    ,'Empate Anula Aposta (Draw No Bet)': 'Draw No Bet'
    ,'Match Winner (Escanteios)': 'Match Winner (Corners)'
    ,'Mais Escanteios': 'Most Corners'
    ,'Empate de Escanteios': 'Corners Draw'
    ,'Handicap de Escanteios': 'Corners Handicap'
    ,'This game has a <strong>Base of %(base)s corners</strong>, indicating high offensive volume. With an Over 8.5 prob. at %(prob)s%%, the scenario is ideal for seeking "Over 8.5 or 9.5" corner markets.': 'This game has a <strong>Base of %(base)s corners</strong>, indicating high offensive volume. With an Over 8.5 prob. at %(prob)s%%, the scenario is ideal for seeking "Over 8.5 or 9.5" corner markets.'
    ,'The base of %(base)s suggests moderate volume. The best strategy here is to look for safety markets like "Over 7.5" or wait for "Live" for better odds.': 'The base of %(base)s suggests moderate volume. The best strategy here is to look for safety markets like "Over 7.5" or wait for "Live" for better odds.'
    ,'Game with a tendency for low lateral volume (Base %(base)s). Be cautious with Over bets; the "Under" market or specific corners by time may be more profitable.': 'Game with a tendency for low lateral volume (Base %(base)s). Be cautious with Over bets; the "Under" market or specific corners by time may be more profitable.'
    ,'Winner & Handicap (Cartões)': 'Winner & Handicap (Cards)'
    ,'Mais Cartões': 'Most Cards'
    ,'Empate de Cartões': 'Cards Draw'
    ,'Handicap': 'Handicap'
    ,'With an average of <strong>%(fouls)s fouls</strong>, we expect a tense game with many stops. The chance of cards (currently %(cards)s yellows/game) is high.': 'With an average of <strong>%(fouls)s fouls</strong>, we expect a tense game with many stops. The chance of cards (currently %(cards)s yellows/game) is high.'
    ,'Game with a tendency to be more fluid (only %(fouls)s fouls on average). The "Under Cards" or "Less than 4.5" market could be a good choice if the referee is not strict.': 'Game with a tendency to be more fluid (only %(fouls)s fouls on average). The "Under Cards" or "Less than 4.5" market could be a good choice if the referee is not strict.'
    ,'Total de Chutes (Over/Under)': 'Total Shots (Over/Under)'
    ,'Chutes ao Gol (Over/Under)': 'Shots on Target (Over/Under)'
    ,'Over 6.5 Chutes no Alvo': 'Over 6.5 Shots on Target'
    ,'Over 7.5 Chutes no Alvo': 'Over 7.5 Shots on Target'
    ,'Over 8.5 Chutes no Alvo': 'Over 8.5 Shots on Target'
    ,'Over 9.5 Chutes no Alvo': 'Over 9.5 Shots on Target'
    ,'Mais Chutes': 'Most Shots'
    ,'Match Winner (Chutes no Alvo)': 'Match Winner (Shots on Target)'
    ,'Mais no Alvo': 'Most on Target'
    ,'Linhas Individuais por Time': 'Individual Team Lines'
    ,'Both teams have accuracy above 30% on target. This is a very strong signal for the <strong>"Both Teams to Score: Yes"</strong> or "Over 1.5/2.5 Goals" market.': 'Both teams have accuracy above 30% on target. This is a very strong signal for the <strong>"Both Teams to Score: Yes"</strong> or "Over 1.5/2.5 Goals" market.'
    ,'Only one of the teams is being lethal in finishing. Consider betting on the "Team Goals" market for the one with higher accuracy.': 'Only one of the teams is being lethal in finishing. Consider betting on the "Team Goals" market for the one with higher accuracy.'
    ,'Both teams are struggling with finishing (Accuracy below 30%). Game with a tendency for few goals, ideal for analyzing the "Under" market.': 'Both teams are struggling with finishing (Accuracy below 30%). Game with a tendency for few goals, ideal for analyzing the "Under" market.'
    ,'Strong': 'Strong'
    ,'Average': 'Average'
    ,'Weak': 'Weak'
    ,'SMART LAY BETS (EXCHANGE)': 'SMART LAY BETS (EXCHANGE)'
    ,'Betting <strong>AGAINST</strong> these outcomes has a high statistical probability of success based on recent data.': 'Betting <strong>AGAINST</strong> these outcomes has a high statistical probability of success based on recent data.'
    ,'Success Chance': 'Success Chance'
    ,'My Profile': 'My Profile'
    ,'Sign Out': 'Sign Out'
    ,'Login': 'Login'
    ,'We use cookies to personalize content and ads, provide social media features, and analyze our traffic. By continuing to use our site, you accept our use of cookies.': 'We use cookies to personalize content and ads, provide social media features, and analyze our traffic. By continuing to use our site, you accept our use of cookies.'
    ,'Learn more': 'Learn more'
    ,'Accept': 'Accept'
    ,'All rights reserved. Professional statistics for analysts.': 'All rights reserved. Professional statistics for analysts.'
    ,'StatsFut - Advanced football statistics, pre-match analysis, Over/Under, BTTS and direct confrontations of the world\'s main leagues.': 'StatsFut - Advanced football statistics, pre-match analysis, Over/Under, BTTS and direct confrontations of the world\'s main leagues.'
    ,'Explore advanced football statistics, pre-match analysis, Over/Under predictions and head-to-head data for the world\'s top leagues. StatsFut - Your data-driven edge.': 'Explore advanced football statistics, pre-match analysis, Over/Under predictions and head-to-head data for the world\'s top leagues. StatsFut - Your data-driven edge.'
    ,'TIMELINE': 'TIMELINE'
    ,'MATCH STATS': 'MATCH STATS'
    ,'No goal events recorded': 'No goal events recorded'
    ,'Corner Kicks': 'Corner Kicks'
    ,'Total Shots': 'Total Shots'
    ,'Yellow Cards': 'Yellow Cards'
    ,'Current Streaks & Sequences': 'Current Streaks & Sequences'
    ,'CURRENT SEQUENCES': 'CURRENT SEQUENCES'
    ,'Consecutive wins': 'Consecutive wins'
    ,'Consecutive draws': 'Consecutive draws'
    ,'Consecutive defeats': 'Consecutive defeats'
    ,'No win': 'No win'
    ,'No draw': 'No draw'
    ,'No defeat': 'No defeat'
    ,'1 goal scored or more': '1 goal scored or more'
    ,'1 goal conceded or more': '1 goal conceded or more'
    ,'No goal scored': 'No goal scored'
    ,'No goal conceded': 'No goal conceded'
    ,'GF+GA over 2.5': 'GF+GA over 2.5'
    ,'GF+GA under 2.5': 'GF+GA under 2.5'
    ,'Scored at least twice': 'Scored at least twice'
    ,'Current Sequences table': 'Current Sequences table'
    ,'Historical statistics': 'Historical statistics'
    ,'(current season vs completed previous season)': '(current season vs completed previous season)'
    ,'Pld': 'Pld'
    ,'Avg Pts': 'Avg Pts'
    ,'Avg GF': 'Avg GF'
    ,'Avg GA': 'Avg GA'
    ,'Username': 'Username'
    ,'Email': 'Email'
    ,'Password': 'Password'
    ,'Confirm Password': 'Confirm Password'
    ,'Welcome Back': 'Welcome Back'
    ,'Sign in to access your premium stats': 'Sign in to access your premium stats'
    ,'Invalid username or password. Please try again.': 'Invalid username or password. Please try again.'
    ,'Create Account': 'Create Account'
    ,'Already have an account?': 'Already have an account?'
    ,'Join StatsFut': 'Join StatsFut'
    ,'Create your account and unlock advanced analytics': 'Create your account and unlock advanced analytics'
    ,'Letters, digits and @/./+/-/_ only.': 'Letters, digits and @/./+/-/_ only.'
    ,'At least 8 characters.': 'At least 8 characters.'
    ,'Don\'t have an account?': 'Don\'t have an account?'
    ,'Odd Justa': 'Fair Odds'
    ,'Ambas Equipes Marcam (BTTS)': 'Both Teams to Score (BTTS)'
    ,'Recomendado': 'Recommended'
    ,'Linha Principal (2.5)': 'Main Line (2.5)'
    ,'Seguro': 'Safe'
    ,'1 a 2 Gols': '1 to 2 Goals'
    ,'2 a 3 Gols': '2 to 3 Goals'
    ,'Base do Jogo': 'Match Base'
    ,'Best Pick': 'Best Pick'
    ,'Red Cards Avg:': 'Red Cards Avg:'
    ,'per game': 'per game'
    ,'Probabilidades Over Cartões': 'Over Cards Probabilities'
    ,'Total de Chutes (Over)': 'Total Shots (Over)'
    ,'Chutes no Alvo': 'Shots on Target'
    ,'Alvo': 'on Target'
    ,'no Alvo': 'on Target'
    ,'Chutes': 'Shots'
}


translations_es = {
    # Existing translations
    'Goal Statistics': 'Estadísticas de Goles',
    'Elite Stats': 'Estadísticas Élite',
    'Home Wins': 'Victorias Local',
    'Draws': 'Empates',
    'Away Wins': 'Victorias Visitante',
    'Over 1.5': 'Más de 1.5',
    'Over 2.5': 'Más de 2.5',
    'Over 3.5': 'Más de 3.5',
    'BTTS': 'Ambos Marcan',
    'Goal Averages': 'Promedios de Goles',
    'Avg Goals': 'Promedio de Goles',
    'Avg Goals For': 'Promedio Goles a Favor',
    'Avg Goals Against': 'Promedio Goles en Contra',
    'Most Common Scores': 'Resultados Comunes',
    'Current Form (Last 8)': 'Rendimiento (Últimos 8)',
    'Goals Stats': 'Estadísticas de Goles',
    'Goals For': 'Goles a Favor',
    'Goals Against': 'Goles en Contra',
    'Timing of Goals': 'Minutos de Goles',
    'Over 0.5': 'Más de 0.5',
    'First Half Goals': 'Goles 1er Tiempo',
    'Second Half Goals': 'Goles 2do Tiempo',
    'Avg Goals/Team': 'Promedio Goles/Equipo',
    'Match Total Goals Stats': 'Estadísticas Goles Totales',
    'Detailed Goal Stats': 'Estadísticas Detalladas de Goles',
    'Clean Sheets %': '% Portería a Cero',
    'Over 2.5 %': '% Más de 2.5',
    'BTTS %': '% Ambos Marcan',

    'Elite Statistics': 'Estadísticas Élite',
    'Season': 'Temporada',
    'Advanced metrics per match across all teams': 'Métricas avanzadas por partido para todos los equipos',
    'Corners (Avg)': 'Córners (Prom)',
    'Yellows (Avg)': 'Amarillas (Prom)',
    'Total Goals': 'Goles Totales',
    'Corners Performance Ranking': 'Ranking de Rendimiento en Córners',
    'Avg per Match': 'Promedio por Partido',
    'matches': 'partidos',
    'For': 'A favor',
    'Ag': 'En contra',
    'Tot': 'Total',
    'No corner data available yet. Processing matches...': 'Aún no hay datos de córners. Procesando partidos...',
    'Cards Averages': 'Promedio de Tarjetas',
    'Goal Minutes Distribution': 'Distribución de Minutos de Goles',
    'goals': 'goles',
    'No goal minute data available.': 'No hay datos de minutos de gol.',
    'League Top Scorers': 'Máximos Goleadores de la Liga',
    'Goals': 'Goles',
    'Pen.': 'Pen.',
    'No top scorer registered for the current season.': 'No hay goleadores registrados para la temporada actual.',
    'Offensive Shots (Avg)': 'Tiros a Puerta (Prom)',
    'Shots': 'Tiros',

    'Date': 'Fecha',
    'Home': 'Local',
    'Away': 'Visitante',
    'Total': 'Total',
    'vs': 'vs',
    'Sequence': 'Racha',
    'Current Streaks': 'Rachas Actuales',
    'GP': 'PJ',
    'W': 'G',
    'D': 'E',
    'L': 'P',
    'W%': '%G',
    'D%': '%E',
    'L%': '%P',
    'All': 'Todos',
    'Opponent': 'Rival',

    # New dashboard translations
    'The <strong>%(league_name)s</strong> is the main professional football league in <strong>%(country)s</strong>.': 'La <strong>%(league_name)s</strong> es la principal liga de fútbol profesional en <strong>%(country)s</strong>.',
    'Currently, the competition leader is <strong>%(leader)s</strong>, leading the league table this season.': 'Actualmente, el líder de la competición es <strong>%(leader)s</strong>, liderando la tabla de clasificación de esta temporada.',
    'StatsFut tracks live football scores, detailed statistics, standings, and performance analysis for all rounds of the competition.': 'StatsFut realiza un seguimiento de los resultados de fútbol en vivo, estadísticas detalladas, clasificaciones y análisis de rendimiento de todas las rondas de la competición.',
    'The average goals per match in the league is <strong>%(avg_goals)s</strong> goals.': 'El promedio de goles por partido en la liga es de <strong>%(avg_goals)s</strong> goles.',
    'About <strong>%(over25)s%%</strong> of matches ended with over 2.5 goals, and in <strong>%(btts)s%%</strong> of the games both teams scored (BTTS).': 'Alrededor del <strong>%(over25)s%%</strong> de los partidos terminaron con más de 2.5 goles, y en el <strong>%(btts)s%%</strong> de los partidos ambos equipos marcaron (BTTS).',
    'The most common result recorded this season is the score of <strong>%(score)s</strong>, occurring in <strong>%(pct)s%%</strong> of all matches played.': 'El resultado más común registrado esta temporada es el marcador de <strong>%(score)s</strong>, que ocurre en el <strong>%(pct)s%%</strong> de todos los partidos jugados.',
    'Resumo da Temporada': 'Resumen de la Temporada',
    'Acompanhe o desempenho completo dos times na <strong>%(league_name)s</strong>. A tabela de classificação acima é atualizada em tempo real após cada partida, fornecendo as posições mais recentes e os pontos acumulados pelas equipes.': 'Siga el rendimiento completo de los equipos en la <strong>%(league_name)s</strong>. La tabla de clasificación anterior se actualiza en tiempo real después de cada partido, proporcionando las últimas posiciones y los puntos acumulados por los equipos.',
    'Nesta temporada, a liga apresenta uma média de <strong>%(avg_g)s gols por partida</strong>. As estatísticas mostram que em <strong>%(btts)s%%</strong> dos confrontos ambas as equipes marcam gols (BTTS), enquanto <strong>%(over25)s%%</strong> das partidas terminam com mais de 2.5 gols no total.': 'Esta temporada, la liga presenta un promedio de <strong>%(avg_g)s goles por partido</strong>. Las estadísticas muestran que en el <strong>%(btts)s%%</strong> de los enfrentamientos ambos equipos marcan (BTTS), mientras que el <strong>%(over25)s%%</strong> de los partidos terminan con más de 2.5 goles en total.',
    'Analise a progressão de cada time, a média de pontos por jogo (PPG) e as taxas de vitória para fazer as melhores projeções. O StatsFut é a sua plataforma definitiva para acompanhar o futebol mundial com dados precisos.': 'Analice la progresión de cada equipo, el promedio de puntos por juego (PPG) y las tasas de victoria para realizar los mejores pronósticos. StatsFut es su plataforma definitiva para seguir el fútbol mundial con datos precisos.',
    'Sobre o': 'Sobre el',
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
    'anos': 'años',
    'About Us': 'Sobre Nosotros',
    'About StatsFut': 'Sobre StatsFut',
    'Our Mission': 'Nuestra Misión',
    'StatsFut was born with the goal of transforming complex football data into clear, actionable insights for fans, bettors, and analysts. We believe that high-quality statistical information should be accessible, fast, and visually intuitive.': 'StatsFut nació con el objetivo de transformar datos complejos de fútbol en información clara y accionable para aficionados, apostadores y analistas. Creemos que la información estadística de alta calidad debe ser accesible, rápida y visualmente intuitiva.',
    'Technology and Precision': 'Tecnología y Precisión',
    'We use cutting-edge technologies to process thousands of events in real-time. Our platform integrates data from various global sources to provide a 360º view of every league, team, and matchup. We focus on advanced metrics that go beyond the scoreline, such as goal probabilities, corner trends, and head-to-head (H2H) analysis.': 'Utilizamos tecnologías de vanguardia para procesar miles de eventos en tiempo real. Nuestra plataforma integra datos de diversas fuentes globales para proporcionar una visión de 360º de cada liga, equipo y enfrentamiento. Nos enfocamos en métricas avanzadas que van más allá del marcador, como probabilidades de gol, tendencias de córners y análisis cara a cara (H2H).',
    'Why StatsFut?': '¿Por qué StatsFut?',
    'In a sea of information, StatsFut stands out for its premium interface and data curation. We don\'t just show numbers; we organize them so you can make smarter decisions, whether to follow your favorite team or conduct professional analysis.': 'En un mar de información, StatsFut se destaca por su interfaz premium y curación de datos. No solo mostramos números; los organizamos para que puedas tomar decisiones más inteligentes, ya sea para seguir a tu equipo favorito o realizar análisis profesionales.',
    'Constantly Evolving': 'Constantemente Evolucionando',
    'We are in an expansion phase, adding new leagues and predictive analysis tools regularly. StatsFut is made by data enthusiasts for football enthusiasts.': 'Estamos en una de las fases de expansión, agregando nuevas ligas y herramientas de análisis predictivo regularmente. StatsFut está hecho por entusiastas de los datos para entusiastas del fútbol.',
    'Last Updated: May 12, 2026': 'Última actualización: 12 de mayo de 2026',
    '1. Introduction': '1. Introducción',
    'Welcome to StatsFut. Your privacy is of extreme importance to us. This Privacy Policy explains how we collect, use, protect, and handle your information when using our website (statsfut.com).': 'Bienvenido a StatsFut. Tu privacidad es de extrema importancia para nosotros. Esta Política de Privacidad explica cómo recopilamos, utilizamos, protegemos y manejamos tu información al usar nuestro sitio web (statsfut.com).',
    '2. Information Collection': '2. Recopilación de Información',
    'We do not require registration to view public statistics. However, we collect basic information automatically through log files and cookies to improve your experience, such as:': 'No requerimos registro para ver estadísticas públicas. Sin embargo, recopilamos información básica automáticamente a través de archivos de registro y cookies para mejorar tu experiencia, como:',
    'IP Address': 'Dirección IP',
    'Browser type': 'Tipo de navegador',
    'Pages visited': 'Páginas visitadas',
    'Time spent on the site': 'Tiempo permanecido en el sitio',
    '3. Cookies and Advertising (Google AdSense)': '3. Cookies y Publicidad (Google AdSense)',
    'We use cookies to provide personalized content and ads. Google, as a third-party vendor, uses cookies (such as the DART cookie) to serve ads based on your visits to our and other sites on the internet.': 'Utilizamos cookies para proporcionar contenido y anuncios personalizados. Google, como proveedor externo, utiliza cookies (como la cookie DART) para mostrar anuncios basados en tus visitas a nuestro sitio y a otros sitios web en internet.',
    'Users may opt-out of the use of the DART cookie by visiting the Google Ad and Content Network Privacy Policy.': 'Los usuarios pueden optar por no utilizar la cookie DART visitando la Política de Privacidad de la Red de Contenido y Anuncios de Google.',
    '4. Use of Information': '4. Uso de la Información',
    'The information collected is used exclusively for:': 'La información recopilada se utiliza exclusivamente para:',
    'Technical maintenance and improvement of the site.': 'Mantenimiento técnico y mejora del sitio.',
    'Traffic analysis (Google Analytics).': 'Análisis de tráfico (Google Analytics).',
    'Ad personalization via advertising networks.': 'Personalización de anuncios a través de redes publicitarias.',
    '5. Security': '5. Seguridad',
    'We employ industry-standard security measures to protect information processed on our site against unauthorized access, alteration, or destruction.': 'Empleamos medidas de seguridad estándar de la industria para proteger la información procesada en nuestro sitio contra el acceso no autorizado, alteración o destrucción.',
    '6. Contact': '6. Contacto',
    'If you have any questions about this Privacy Policy, please contact us through our official channels.': 'Si tienes alguna pregunta sobre esta Política de Privacidad, por favor contáctanos a través de nuestros canales oficiales.',
    '1. Acceptance of Terms': '1. Aceptación de los Términos',
    'By accessing and using the StatsFut website (statsfut.com), you agree to comply with and be bound by the following terms and conditions of use. If you do not agree with any part of these terms, you must not use our website.': 'Al acceder y utilizar el sitio web de StatsFut (statsfut.com), aceptas cumplir y estar sujeto a los siguientes términos y condiciones de uso. Si no estás de acuerdo con alguna parte de estos términos, no debes utilizar nuestro sitio web.',
    '3. Disclaimer': '3. Descargo de Responsabilidad',
    'While we strive to ensure data accuracy, StatsFut does not guarantee that the information is free of errors or omissions. We are not responsible for financial losses or decisions made based on the information contained on this site. Football is unpredictable, and past statistics do not guarantee future results.': 'Aunque nos esforzamos por garantizar la precisión de los datos, StatsFut no garantiza que la información esté libre de errores u omisiones. No somos responsables de pérdidas financieras o decisiones tomadas basadas en la información contenida en este sitio. El fútbol es impredecible y las estadísticas pasadas no garantizan resultados futuros.',
    '4. Intellectual Property': '4. Propiedad Intelectual',
    'The design, layout, logos, and original texts of StatsFut are intellectual property protected by copyright laws. Unauthorized reproduction of material from this site is prohibited.': 'El diseño, la disposición, los logotipos y los textos originales de StatsFut son propiedad intelectual protegida por las leyes de derechos de autor. Queda prohibida la reproducción no autorizada del material de este sitio.',
    '5. Third-Party Links': '5. Enlaces de Terceros',
    'Our site may contain links to third-party websites (such as advertisers or partners). We have no control over the content or privacy practices of those sites and assume no responsibility for them.': 'Nuestro sitio puede contener enlaces a sitios web de terceros (como anunciantes o socios). No tenemos control sobre el contenido o las prácticas de privacidad de esos sitios y no asumimos ninguna responsabilidad por ellos.',
    '6. Changes to Terms': '6. Cambios en los Términos',
    'StatsFut reserves the right to modify these terms at any time without prior notice. We recommend periodic review of this page.': 'StatsFut se reserva el derecho de modificar estos términos en cualquier momento sin previo aviso. Recomendamos la revisión periódica de esta página.',
    'Get in Touch': 'Ponte en Contacto',
    'Have questions about our data or suggestions for new features? We\'d love to hear from you.': '¿Tienes preguntas sobre nuestros datos o sugerencias para nuevas funciones? Nos encantaría saber de ti.',
    'For general inquiries and support:': 'Para consultas generales y soporte:',
    'For advertising and partnerships:': 'Para publicidad y alianzas:',
    'Our Response Time': 'Nuestro Tiempo de Respuesta',
    'We typically respond to all inquiries within 24-48 business hours. Thank you for your patience.': 'Normalmente respondemos a todas las consultas dentro de 24-48 horas hábiles. Gracias por tu paciencia.',
    'Score': 'Resultado',
    'Count': 'Cantidad',
    'Team': 'Equipo',
    'GP': 'PJ',
    'Pts': 'Pts',
    'Rank': 'Pos',
    'Points earned in the last 8 matches': 'Puntos ganados en los últimos 8 partidos',
    'Total': 'Total',
    'Last 8': 'Últimos 8',
    'Home': 'Local',
    'Away': 'Visitante',
    'Avg': 'Prom',
    'BTS': 'AM',
    'CS': 'AC',
    'FTS': 'SM',
    'WTN': 'VSC',
    'LTN': 'PSC',
    'Games Played': 'Partidos Jugados',
    'Average Total Goals': 'Promedio Total de Goles',
    'Both Teams Scored': 'Ambos Equipos Marcaron',
    'Clean Sheets': 'Porterías a Cero',
    'Failed to Score': 'Sin Marcar',
    'Win to Nil': 'Ganar sin Conceder',
    'Lose to Nil': 'Perder sin Marcar',
    'League Average': 'Promedio de la Liga',
    'Half-Time Stats': 'Estadísticas del Primer Tiempo',
    'Both Teams to Score': 'Ambos Equipos Marcan',
    'Detailed Statistics and Elite Analysis': 'Estadísticas Detalladas y Análisis Élite',
    'Advanced statistics and detailed analysis for the %(league_name)s (%(country)s) league, %(year)s season. Explore in-depth information about corner averages, distribution of yellow and red cards per game, team discipline, volume of shots, and the exact moment goals happen throughout the 90 minutes.': 'Estadísticas avanzadas y análisis detallado de la liga %(league_name)s (%(country)s), temporada %(year)s. Explore información detallada sobre promedios de tiros de esquina, distribución de tarjetas amarillas y rojas por partido, disciplina del equipo, volumen de tiros y el momento exacto en que ocurren los goles a lo largo de los 90 minutos.',
    'So far, the overall championship average records %(avg_corners)s corners taken per match and a disciplinary average of %(avg_yellow)s yellow cards received per game. This data provides a complete overview of the tactical behavior trends and game intensity of each team in the competition.': 'Hasta el momento, el promedio general del campeonato registra %(avg_corners)s tiros de esquina por partido y un promedio disciplinario de %(avg_yellow)s tarjetas amarillas recibidas por juego. Estos datos proporcionan una visión completa de las tendencias de comportamiento táctico y la intensidad de juego de cada equipo en la competición.',
    'Goal Statistics and Over/Under Trends': 'Estadísticas de Goles y Tendencias Over/Under',
    'Complete statistics and goal analysis for the %(league_name)s (%(country)s) league. This page gathers detailed metrics on goal averages, Over/Under markets, Both Teams to Score (BTTS), Clean Sheets, and the most frequent scores to assist in your sports analysis.': 'Estadísticas completas y análisis de goles de la liga %(league_name)s (%(country)s). Esta página recopila métricas detalladas sobre promedios de goles, mercados Over/Under, Ambos Equipos Marcan (BTTS), Porterías a Cero y los resultados más frecuentes para ayudar en su análisis deportivo.',
    'The current season of the competition records a general average of %(avg_goals)s goals per game. In terms of market patterns, %(over15)s%% of matches exceeded the 1.5 goal mark and %(over25)s%% recorded more than 2.5 goals. The Both Teams to Score (BTTS) rate is at %(btts)s%%, while the percentage of games where at least one team did not concede any goals (Clean Sheet) is %(cs)s%%.': 'La temporada actual de la competición registra un promedio general de %(avg_goals)s goles por partido. En cuanto a los patrones del mercado, el %(over15)s%% de los partidos superó la línea de 1.5 goles y el %(over25)s%% registró más de 2.5 goles. La tasa de Ambos Equipos Marcan (BTTS) se sitúa en el %(btts)s%%, mientras que el porcentaje de partidos donde al menos un equipo no recibió goles (Portería a Cero) es del %(cs)s%%.'
    ,'Estatísticas completas e previsões detalhadas para a partida entre': 'Estadísticas completas y pronósticos detallados para el partido entre'
    ,'e': 'y'
    ,'válida pela': 'válido para la'
    ,'Analise as probabilidades de Ambas Marcam (BTTS), Mais de 2.5 Gols, cantos, cartões e histórico de confrontos diretos (H2H) para apoiar suas análises e palpites esportivos baseados em dados.': 'Analice las probabilidades de Ambos Marcan (BTTS), Más de 2.5 Goles, córners, tarjetas e historial de enfrentamientos directos (H2H) para respaldar sus análisis y pronósticos deportivos basados en datos.'
    ,'Gols & Tempos': 'Goles y Tiempos'
    ,'Escanteios': 'Córners'
    ,'Cartões': 'Tarjetas'
    ,'Chutes': 'Tiros'
    ,'Especiais & Combos': 'Especiales y Combos'
    ,'Ambas Marcam Detalhado': 'Ambos Marcan Detallado'
    ,'Faixa de Gols (Partida)': 'Rango de Goles (Partido)'
    ,'Faixa (1º Tempo)': 'Rango (1er Tiempo)'
    ,'Faixa (2º Tempo)': 'Rango (2do Tiempo)'
    ,'Margem de Vitória Exata': 'Margen de Victoria Exacto'
    ,'por 1 gol': 'por 1 gol'
    ,'por 2 gols': 'por 2 goles'
    ,'por 3+ gols': 'por 3+ goles'
    ,'Empate com gols': 'Empate con goles'
    ,'Empate sem gols (0-0)': 'Empate sin goles (0-0)'
    ,'Metades & Tempos': 'Mitades y Tiempos'
    ,'Mais gols no 1º Tempo': 'Más goles en el 1er Tiempo'
    ,'Mais gols no 2º Tempo': 'Más goles en el 2do Tiempo'
    ,'Metades com gols iguais': 'Mitades con goles iguales'
    ,'Marcar em Ambos os Tempos': 'Marcar en Ambos Tiempos'
    ,'Marcar Ambos Tempos': 'Marcar Ambos Tiempos'
    ,'Marcar pelo menos Um': 'Marcar al menos Uno'
    ,'Intervalo / Fim do Jogo': 'Descanso / Final del Partido'
    ,'Resultado 1º Tempo': 'Resultado 1er Tiempo'
    ,'Vence HT': 'Gana HT'
    ,'Empate HT': 'Empate HT'
    ,'Vencedor + Ambos Marcam': 'Ganador + Ambos Marcan'
    ,'Sim': 'Sí'
    ,'Empate': 'Empate'
    ,'Chance Dupla + Faixa de Gols': 'Doble Oportunidad + Rango de Goles'
    ,'Gols': 'Goles'
    ,'Handicap Asiático & Europeu': 'Hándicap Asiático y Europeo'
    ,'Empate Anula Aposta (Draw No Bet)': 'Empate Anula Apuesta (Draw No Bet)'
    ,'Match Winner (Escanteios)': 'Ganador del Partido (Córners)'
    ,'Mais Escanteios': 'Más Córners'
    ,'Empate de Escanteios': 'Empate de Córners'
    ,'Handicap de Escanteios': 'Hándicap de Córners'
    ,'This game has a <strong>Base of %(base)s corners</strong>, indicating high offensive volume. With an Over 8.5 prob. at %(prob)s%%, the scenario is ideal for seeking "Over 8.5 or 9.5" corner markets.': 'Este partido tiene una <strong>Base de %(base)s córners</strong>, lo que indica un alto volumen ofensivo. Con una prob. de Más de 8.5 al %(prob)s%%, el escenario es ideal para buscar mercados de "Más de 8.5 o 9.5" córners.'
    ,'The base of %(base)s suggests moderate volume. The best strategy here is to look for safety markets like "Over 7.5" or wait for "Live" for better odds.': 'La base de %(base)s sugiere un volumen moderado. La mejor estrategia aquí es buscar mercados seguros como "Más de 7.5" o esperar al "En Vivo" para mejores cuotas.'
    ,'Game with a tendency for low lateral volume (Base %(base)s). Be cautious with Over bets; the "Under" market or specific corners by time may be more profitable.': 'Partido con tendencia a bajo volumen lateral (Base %(base)s). Tenga cuidado con las apuestas de Más; el mercado de "Menos" o córners específicos por tiempo pueden ser más rentables.'
    ,'Winner & Handicap (Cartões)': 'Ganador y Hándicap (Tarjetas)'
    ,'Mais Cartões': 'Más Tarjetas'
    ,'Empate de Cartões': 'Empate de Tarjetas'
    ,'Handicap': 'Hándicap'
    ,'With an average of <strong>%(fouls)s fouls</strong>, we expect a tense game with many stops. The chance of cards (currently %(cards)s yellows/game) is high.': 'Con un promedio de <strong>%(fouls)s faltas</strong>, esperamos un partido tenso y con muchas interrupciones. La probabilidad de tarjetas (actualmente %(cards)s amarillas/partido) es alta.'
    ,'Game with a tendency to be more fluid (only %(fouls)s fouls on average). The "Under Cards" or "Less than 4.5" market could be a good choice if the referee is not strict.': 'Partido con tendencia a ser más fluido (solo %(fouls)s faltas en promedio). El mercado de "Menos Tarjetas" o "Menos de 4.5" podría ser una buena opción si el árbitro no es estricto.'
    ,'Total de Chutes (Over/Under)': 'Total Tiros (Over/Under)'
    ,'Chutes ao Gol (Over/Under)': 'Tiros a Puerta (Over/Under)'
    ,'Over 6.5 Chutes no Alvo': 'Más de 6.5 Tiros a Puerta'
    ,'Over 7.5 Chutes no Alvo': 'Más de 7.5 Tiros a Puerta'
    ,'Over 8.5 Chutes no Alvo': 'Más de 8.5 Tiros a Puerta'
    ,'Over 9.5 Chutes no Alvo': 'Más de 9.5 Tiros a Puerta'
    ,'Mais Chutes': 'Más Tiros'
    ,'Match Winner (Chutes no Alvo)': 'Ganador del Partido (Tiros a Puerta)'
    ,'Mais no Alvo': 'Más a Puerta'
    ,'Linhas Individuais por Time': 'Líneas Individuales por Equipo'
    ,'Both teams have accuracy above 30% on target. This is a very strong signal for the <strong>"Both Teams to Score: Yes"</strong> or "Over 1.5/2.5 Goals" market.': 'Ambos equipos tienen una precisión superior al 30%% a puerta. Esta es una señal muy fuerte para el mercado de <strong>"Ambos Equipos Marcan: Sí"</strong> o "Más de 1.5/2.5 Goles".'
    ,'Only one of the teams is being lethal in finishing. Consider betting on the "Team Goals" market for the one with higher accuracy.': 'Solo uno de los equipos está siendo letal en la definición. Considere apostar en el mercado de "Goles del Equipo" para el que tiene mayor precisión.'
    ,'Both teams are struggling with finishing (Accuracy below 30%). Game with a tendency for few goals, ideal for analyzing the "Under" market.': 'Ambos equipos tienen dificultades con la definición (precisión inferior al 30%%). Partido con tendencia a pocos goles, ideal para analizar el mercado de "Menos".'
    ,'Strong': 'Fuerte'
    ,'Average': 'Regular'
    ,'Weak': 'Frágil'
    ,'SMART LAY BETS (EXCHANGE)': 'APUESTAS SMART LAY (EXCHANGE)'
    ,'Betting <strong>AGAINST</strong> these outcomes has a high statistical probability of success based on recent data.': 'Apostar <strong>EN CONTRA</strong> de estos resultados tiene una alta probabilidad estadística de éxito basada en datos recientes.'
    ,'Success Chance': 'Prob. de Éxito'
    ,'My Profile': 'Mi Perfil'
    ,'Sign Out': 'Cerrar Sesión'
    ,'Login': 'Iniciar Sesión'
    ,'We use cookies to personalize content and ads, provide social media features, and analyze our traffic. By continuing to use our site, you accept our use of cookies.': 'Utilizamos cookies para personalizar el contenido y los anuncios, proporcionar funciones de redes sociales y analizar nuestro tráfico. Al continuar usando nuestro sitio, acepta nuestro uso de cookies.'
    ,'Learn more': 'Más información'
    ,'Accept': 'Aceptar'
    ,'All rights reserved. Professional statistics for analysts.': 'Todos los derechos reservados. Estadísticas profesionales para analistas.'
    ,'StatsFut - Advanced football statistics, pre-match analysis, Over/Under, BTTS and direct confrontations of the world\'s main leagues.': 'StatsFut - Estadísticas avanzadas de fútbol, análisis previo al partido, Over/Under, BTTS y enfrentamientos directos de las principales ligas del mundo.'
    ,'Explore advanced football statistics, pre-match analysis, Over/Under predictions and head-to-head data for the world\'s top leagues. StatsFut - Your data-driven edge.': 'Explore estadísticas avanzadas de fútbol, análisis previos a partidos, predicciones Over/Under y datos cara a cara para las principales ligas del mundo. StatsFut: su ventaja basada en datos.'
    ,'TIMELINE': 'LÍNEA DE TIEMPO'
    ,'MATCH STATS': 'ESTADÍSTICAS DEL PARTIDO'
    ,'No goal events recorded': 'No se registraron goles'
    ,'Corner Kicks': 'Saques de Esquina'
    ,'Total Shots': 'Tiros Totales'
    ,'Yellow Cards': 'Tarjetas Amarillas'
    ,'Current Streaks & Sequences': 'Rachas y Secuencias Actuales'
    ,'CURRENT SEQUENCES': 'SECUENCIAS ACTUALES'
    ,'Consecutive wins': 'Victorias consecutivas'
    ,'Consecutive draws': 'Empates consecutivos'
    ,'Consecutive defeats': 'Derrotas consecutivas'
    ,'No win': 'Sin ganar'
    ,'No draw': 'Sin empatar'
    ,'No defeat': 'Sin perder'
    ,'1 goal scored or more': '1 gol marcado o más'
    ,'1 goal conceded or more': '1 gol recibido o más'
    ,'No goal scored': 'Sin goles marcados'
    ,'No goal conceded': 'Sin goles recibidos'
    ,'GF+GA over 2.5': 'GF+GC más de 2.5'
    ,'GF+GA under 2.5': 'GF+GC menos de 2.5'
    ,'Scored at least twice': 'Marcó al menos dos goles'
    ,'Current Sequences table': 'Tabla de Secuencias Actuales'
    ,'Historical statistics': 'Estadísticas históricas'
    ,'(current season vs completed previous season)': '(temporada actual vs temporada anterior completada)'
    ,'Pld': 'PJ'
    ,'Avg Pts': 'Prom Pts'
    ,'Avg GF': 'Prom GF'
    ,'Avg GA': 'Prom GC'
    ,'Username': 'Usuario'
    ,'Email': 'Correo electrónico'
    ,'Password': 'Contraseña'
    ,'Confirm Password': 'Confirmar Contraseña'
    ,'Welcome Back': 'Bienvenido de nuevo'
    ,'Sign in to access your premium stats': 'Inicie sesión para acceder a sus estadísticas premium'
    ,'Invalid username or password. Please try again.': 'Usuario o contraseña incorrectos. Por favor, inténtelo de nuevo.'
    ,'Create Account': 'Crear Cuenta'
    ,'Already have an account?': '¿Ya tiene una cuenta?'
    ,'Join StatsFut': 'Únase a StatsFut'
    ,'Create your account and unlock advanced analytics': 'Cree su cuenta y acceda a estadísticas avanzadas'
    ,'Letters, digits and @/./+/-/_ only.': 'Solo letras, números y @/./+/-/_ .'
    ,'At least 8 characters.': 'Al menos 8 caracteres.'
    ,'Don\'t have an account?': '¿No tiene una cuenta?'
    ,'Odd Justa': 'Cuota Justa'
    ,'Ambas Equipes Marcam (BTTS)': 'Ambos Equipos Marcan (BTTS)'
    ,'Recomendado': 'Recomendado'
    ,'Linha Principal (2.5)': 'Línea Principal (2.5)'
    ,'Seguro': 'Seguro'
    ,'1 a 2 Gols': '1 a 2 Goles'
    ,'2 a 3 Gols': '2 a 3 Goles'
    ,'Base do Jogo': 'Base del Partido'
    ,'Best Pick': 'Mejor Opción'
    ,'Red Cards Avg:': 'Prom. de Tarjetas Rojas:'
    ,'per game': 'por juego'
    ,'Probabilidades Over Cartões': 'Probabilidades Más de Tarjetas'
    ,'Total de Chutes (Over)': 'Total de Tiros (Más de)'
    ,'Chutes no Alvo': 'Tiros a Puerta'
    ,'Alvo': 'a Puerta'
    ,'no Alvo': 'a Puerta'
    ,'Chutes': 'Tiros'
}

translations_de = {
    # Existing translations
    'Goal Statistics': 'Tor-Statistiken',
    'Elite Stats': 'Elite-Statistiken',
    'Home Wins': 'Heimsiege',
    'Draws': 'Unentschieden',
    'Away Wins': 'Auswärtssiege',
    'Over 1.5': 'Über 1.5',
    'Over 2.5': 'Über 2.5',
    'Over 3.5': 'Über 3.5',
    'BTTS': 'Beide treffen',
    'Goal Averages': 'Tordurchschnitt',
    'Avg Goals': 'Durchschnitt Tore',
    'Avg Goals For': 'Tore erzielt (Durchschnitt)',
    'Avg Goals Against': 'Gegentore (Durchschnitt)',
    'Most Common Scores': 'Häufigste Ergebnisse',
    'Current Form (Last 8)': 'Aktuelle Form (Letzte 8)',
    'Goals Stats': 'Tor-Statistiken',
    'Goals For': 'Erzielte Tore',
    'Goals Against': 'Gegentore',
    'Timing of Goals': 'Zeitpunkt der Tore',
    'Over 0.5': 'Über 0.5',
    'First Half Goals': 'Tore 1. Halbzeit',
    'Second Half Goals': 'Tore 2. Halbzeit',
    'Avg Goals/Team': 'Durchschnitt Tore/Team',
    'Match Total Goals Stats': 'Gesamttore Statistiken',
    'Detailed Goal Stats': 'Detaillierte Tor-Statistiken',
    'Clean Sheets %': 'Ohne Gegentor %',
    'Over 2.5 %': 'Über 2.5 %',
    'BTTS %': 'Beide treffen %',

    'Elite Statistics': 'Elite-Statistiken',
    'Season': 'Saison',
    'Advanced metrics per match across all teams': 'Erweiterte Metriken pro Spiel für alle Teams',
    'Corners (Avg)': 'Ecken (Durchschnitt)',
    'Yellows (Avg)': 'Gelbe Karten (Durchschnitt)',
    'Total Goals': 'Gesamttore',
    'Corners Performance Ranking': 'Ecken-Leistungsranking',
    'Avg per Match': 'Durchschnitt pro Spiel',
    'matches': 'Spiele',
    'For': 'Dafür',
    'Ag': 'Dagegen',
    'Tot': 'Gesamt',
    'No corner data available yet. Processing matches...': 'Noch keine Eckdaten verfügbar. Verarbeite Spiele...',
    'Cards Averages': 'Karten-Durchschnitt',
    'Goal Minutes Distribution': 'Torminuten-Verteilung',
    'goals': 'Tore',
    'No goal minute data available.': 'Keine Torminuten-Daten verfügbar.',
    'League Top Scorers': 'Liga Torschützenkönige',
    'Goals': 'Tore',
    'Pen.': 'Elf.',
    'No top scorer registered for the current season.': 'Kein Torschützenkönig für die aktuelle Saison registriert.',
    'Offensive Shots (Avg)': 'Torschüsse (Durchschnitt)',
    'Shots': 'Schüsse',

    'Date': 'Datum',
    'Home': 'Heim',
    'Away': 'Auswärts',
    'Total': 'Gesamt',
    'vs': 'vs',
    'Sequence': 'Serie',
    'Current Streaks': 'Aktuelle Serien',
    'GP': 'Sp',
    'W': 'S',
    'D': 'U',
    'L': 'N',
    'W%': 'S%',
    'D%': 'U%',
    'L%': 'N%',
    'All': 'Alle',
    'Opponent': 'Gegner',

    # New dashboard translations
    'The <strong>%(league_name)s</strong> is the main professional football league in <strong>%(country)s</strong>.': 'Die <strong>%(league_name)s</strong> ist die wichtigste professionelle Fußballliga in <strong>%(country)s</strong>.',
    'Currently, the competition leader is <strong>%(leader)s</strong>, leading the league table this season.': 'Derzeit ist <strong>%(leader)s</strong> der Tabellenführer und führt die Tabelle in dieser Saison an.',
    'StatsFut tracks live football scores, detailed statistics, standings, and performance analysis for all rounds of the competition.': 'StatsFut verfolgt Live-Fußballergebnisse, detaillierte Statistiken, Tabellen und Leistungsanalysen für alle Spieltage des Wettbewerbs.',
    'The average goals per match in the league is <strong>%(avg_goals)s</strong> goals.': 'Der Tordurchschnitt pro Spiel in der Liga liegt bei <strong>%(avg_goals)s</strong> Toren.',
    'About <strong>%(over25)s%%</strong> of matches ended with over 2.5 goals, and in <strong>%(btts)s%%</strong> of the games both teams scored (BTTS).': 'Etwa <strong>%(over25)s%%</strong> der Spiele endeten mit über 2,5 Toren, und in <strong>%(btts)s%%</strong> der Spiele haben beide Teams getroffen (BTTS).',
    'The most common result recorded this season is the score of <strong>%(score)s</strong>, occurring in <strong>%(pct)s%%</strong> of all matches played.': 'Das häufigste Ergebnis in dieser Saison ist <strong>%(score)s</strong>, was in <strong>%(pct)s%%</strong> aller gespielten Spiele vorkommt.',
    'Resumo da Temporada': 'Saison-Zusammenfassung',
    'Acompanhe o desempenho completo dos times na <strong>%(league_name)s</strong>. A tabela de classificação acima é atualizada em tempo real após cada partida, fornecendo as posições mais recentes e os pontos acumulados pelas equipes.': 'Verfolgen Sie die komplette Leistung der Teams in der <strong>%(league_name)s</strong>. Die obige Tabelle wird nach jedem Spiel in Echtzeit aktualisiert und liefert die neuesten Platzierungen und gesammelten Punkte der Teams.',
    'Nesta temporada, a liga apresenta uma média de <strong>%(avg_g)s gols por partida</strong>. As estatísticas mostram que em <strong>%(btts)s%%</strong> dos confrontos ambas as equipes marcam gols (BTTS), enquanto <strong>%(over25)s%%</strong> das partidas terminam com mais de 2.5 gols no total.': 'In dieser Saison weist die Liga einen Durchschnitt von <strong>%(avg_g)s Toren pro Spiel</strong> auf. Die Statistiken zeigen, dass in <strong>%(btts)s%%</strong> der Duelle beide Teams treffen (BTTS), während <strong>%(over25)s%%</strong> der Spiele mit über 2,5 Toren enden.',
    'Analise a progressão de cada time, a média de pontos por jogo (PPG) e as taxas de vitória para fazer as melhores projeções. O StatsFut é a sua plataforma definitiva para acompanhar o futebol mundial com dados precisos.': 'Analysieren Sie die Entwicklung jedes Teams, die durchschnittlichen Punkte pro Spiel (PPG) und die Siegquoten, um die besten Vorhersagen zu treffen. StatsFut ist Ihre ultimative Plattform, um den Weltfußball mit präzisen Daten zu verfolgen.'
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
    'anos': 'Jahre',
    'About Us': 'Über uns',
    'About StatsFut': 'Über StatsFut',
    'Our Mission': 'Unsere Mission',
    'StatsFut was born with the goal of transforming complex football data into clear, actionable insights for fans, bettors, and analysts. We believe that high-quality statistical information should be accessible, fast, and visually intuitive.': 'StatsFut wurde mit dem Ziel geboren, komplexe Fußballdaten in klare, umsetzbare Erkenntnisse für Fans, Wettende und Analysten zu verwandeln. Wir glauben, dass qualitativ hochwertige statistische Informationen zugänglich, schnell und visuell intuitiv sein sollten.',
    'Technology and Precision': 'Technologie und Präzision',
    'We use cutting-edge technologies to process thousands of events in real-time. Our platform integrates data from various global sources to provide a 360º view of every league, team, and matchup. We focus on advanced metrics that go beyond the scoreline, such as goal probabilities, corner trends, and head-to-head (H2H) analysis.': 'Wir nutzen modernste Technologien, um Tausende von Ereignissen in Echtzeit zu verarbeiten. Unsere Plattform integriert Daten aus verschiedenen globalen Quellen, um eine 360-Grad-Ansicht jeder Liga, jedes Teams und jeder Begegnung zu bieten. Wir konzentrieren uns auf fortschrittliche Kennzahlen, die über das reine Spielergebnis hinausgehen, wie Torwahrscheinlichkeiten, Eckentrends und Head-to-Head-Analysen (H2H).',
    'Why StatsFut?': 'Warum StatsFut?',
    'In a sea of information, StatsFut stands out for its premium interface and data curation. We don\'t just show numbers; we organize them so you can make smarter decisions, whether to follow your favorite team or conduct professional analysis.': 'In einer Flut von Informationen zeichnet sich StatsFut durch seine Premium-Benutzeroberfläche und Datenkuratierung aus. Wir zeigen nicht nur Zahlen; wir organisieren sie, damit Sie intelligentere Entscheidungen treffen können, sei es, um Ihrem Lieblingsteam zu folgen oder professionelle Analysen durchzuführen.',
    'Constantly Evolving': 'Ständige Weiterentwicklung',
    'We are in an expansion phase, adding new leagues and predictive analysis tools regularly. StatsFut is made by data enthusiasts for football enthusiasts.': 'Wir befinden uns in einer Expansionsphase und fügen regelmäßig neue Ligen und prädiktive Analysetools hinzu. StatsFut wird von Datenbegeisterten für Fußballbegeisterten gemacht.',
    'Last Updated: May 12, 2026': 'Zuletzt aktualisiert: 12. Mai 2026',
    '1. Introduction': '1. Einführung',
    'Welcome to StatsFut. Your privacy is of extreme importance to us. This Privacy Policy explains how we collect, use, protect, and handle your information when using our website (statsfut.com).': 'Willkommen bei StatsFut. Ihre Privatsphäre ist uns von äußerster Wichtigkeit. Diese Datenschutzrichtlinie erklärt, wie wir Ihre Informationen sammeln, verwenden, schützen und handhaben, wenn Sie unsere Website (statsfut.com) nutzen.',
    '2. Information Collection': '2. Informationserhebung',
    'We do not require registration to view public statistics. However, we collect basic information automatically through log files and cookies to improve your experience, such as:': 'Wir verlangen keine Registrierung zur Einsicht öffentlicher Statistiken. Wir sammeln jedoch automatisch grundlegende Informationen durch Protokolldateien und Cookies, um Ihr Erlebnis zu verbessern, wie z. B.:',
    'IP Address': 'IP-Adresse',
    'Browser type': 'Browsertyp',
    'Pages visited': 'Besuchte Seiten',
    'Time spent on the site': 'Verbrachte Zeit auf der Website',
    '3. Cookies and Advertising (Google AdSense)': '3. Cookies und Werbung (Google AdSense)',
    'We use cookies to provide personalized content and ads. Google, as a third-party vendor, uses cookies (such as the DART cookie) to serve ads based on your visits to our and other sites on the internet.': 'Wir verwenden Cookies, um personalisierte Inhalte und Anzeigen bereitzustellen. Google als Drittanbieter verwendet Cookies (wie das DART-Cookie), um Anzeigen basierend auf Ihren Besuchen auf unserer und anderen Websites im Internet zu schalten.',
    'Users may opt-out of the use of the DART cookie by visiting the Google Ad and Content Network Privacy Policy.': 'Nutzer können die Verwendung des DART-Cookies deaktivieren, indem sie die Datenschutzrichtlinie des Werbenetzwerks und Content-Werbenetzwerks von Google besuchen.',
    '4. Use of Information': '4. Verwendung von Informationen',
    'The information collected is used exclusively for:': 'Die gesammelten Informationen werden ausschließlich verwendet für:',
    'Technical maintenance and improvement of the site.': 'Technische Wartung und Verbesserung der Website.',
    'Traffic analysis (Google Analytics).': 'Traffic-Analyse (Google Analytics).',
    'Ad personalization via advertising networks.': 'Anzeigenpersonalisierung über Werbenetzwerke.',
    '5. Security': '5. Sicherheit',
    'We employ industry-standard security measures to protect information processed on our site against unauthorized access, alteration, or destruction.': 'Wir setzen Sicherheitsmaßnahmen nach Branchenstandard ein, um die auf unserer Website verarbeiteten Informationen vor unbefugtem Zugriff, Änderung oder Zerstörung zu schützen.',
    '6. Contact': '6. Kontakt',
    'If you have any questions about this Privacy Policy, please contact us through our official channels.': 'Wenn Sie Fragen zu dieser Datenschutzrichtlinie haben, kontaktieren Sie uns bitte über unsere offiziellen Kanäle.',
    '1. Acceptance of Terms': '1. Annahme der Bedingungen',
    'By accessing and using the StatsFut website (statsfut.com), you agree to comply with and be bound by the following terms and conditions of use. If you do not agree with any part of these terms, you must not use our website.': 'Durch den Zugriff auf und die Nutzung der StatsFut-Website (statsfut.com) erklären Sie sich mit den folgenden Nutzungsbedingungen einverstanden. Wenn Sie mit Teilen dieser Bedingungen nicht einverstanden sind, dürfen Sie unsere Website nicht nutzen.',
    '3. Disclaimer': '3. Haftungsausschluss',
    'While we strive to ensure data accuracy, StatsFut does not guarantee that the information is free of errors or omissions. We are not responsible for financial losses or decisions made based on the information contained on this site. Football is unpredictable, and past statistics do not guarantee future results.': 'Obwohl wir uns um Datengenauigkeit bemühen, garantiert StatsFut nicht, dass die Informationen frei von Fehlern oder Auslassungen sind. Wir sind nicht verantwortlich für finanzielle Verluste oder Entscheidungen, die auf der Grundlage der auf dieser Website enthaltenen Informationen getroffen werden. Fußball ist unberechenbar, und vergangene Statistiken garantieren keine zukünftigen Ergebnisse.',
    '4. Intellectual Property': '4. Geistiges Eigentum',
    'The design, layout, logos, and original texts of StatsFut are intellectual property protected by copyright laws. Unauthorized reproduction of material from this site is prohibited.': 'Das Design, das Layout, die Logos und die Originaltexte von StatsFut sind geistiges Eigentum, das durch Urheberrechtsgesetze geschützt ist. Die unbefugte Vervielfältigung von Material dieser Website ist untersagt.',
    '5. Third-Party Links': '5. Links von Drittanbietern',
    'Our site may contain links to third-party websites (such as advertisers or partners). We have no control over the content or privacy practices of those sites and assume no responsibility for them.': 'Unsere Website kann Links zu Websites Dritter enthalten (z. B. Werbetreibende oder Partner). Wir haben keine Kontrolle über den Inhalt oder die Datenschutzpraktiken dieser Websites und übernehmen keine Verantwortung für sie.',
    '6. Changes to Terms': '6. Änderungen der Bedingungen',
    'StatsFut reserves the right to modify these terms at any time without prior notice. We recommend periodic review of this page.': 'StatsFut behält sich das Recht vor, diese Bedingungen jederzeit und ohne vorherige Ankündigung zu ändern. Wir empfehlen eine regelmäßige Überprüfung dieser Seite.',
    'Get in Touch': 'In Kontakt treten',
    'Have questions about our data or suggestions for new features? We\'d love to hear from you.': 'Haben Sie Fragen zu unseren Daten oder Vorschläge für neue Funktionen? Wir würden uns freuen, von Ihnen zu hören.',
    'For general inquiries and support:': 'Für allgemeine Anfragen und Support:',
    'For advertising and partnerships:': 'Für Werbung und Partnerschaften:',
    'Our Response Time': 'Unsere Antwortzeit',
    'We typically respond to all inquiries within 24-48 business hours. Thank you for your patience.': 'Wir antworten in der Regel auf alle Anfragen innerhalb von 24–48 Geschäftsstunden. Vielen Dank für Ihre Geduld.',
    'Score': 'Ergebnis',
    'Count': 'Anzahl',
    'Team': 'Team',
    'GP': 'Sp',
    'Pts': 'Pkt',
    'Rank': 'Rang',
    'Points earned in the last 8 matches': 'In den letzten 8 Spielen erzielt Punkte',
    'Total': 'Gesamt',
    'Last 8': 'Letzte 8',
    'Home': 'Heim',
    'Away': 'Auswärts',
    'Avg': 'Schnitt',
    'BTS': 'BTTS',
    'CS': 'CS',
    'FTS': 'FTS',
    'WTN': 'WTN',
    'LTN': 'LTN',
    'Games Played': 'Gespielte Spiele',
    'Average Total Goals': 'Durchschnittliche Tore gesamt',
    'Both Teams Scored': 'Beide Teams trafen',
    'Clean Sheets': 'Ohne Gegentor',
    'Failed to Score': 'Ohne Torerfolg',
    'Win to Nil': 'Sieg ohne Gegentor',
    'Lose to Nil': 'Niederlage ohne Torerfolg',
    'League Average': 'Liga-Durchschnitt',
    'Half-Time Stats': 'Halbzeit-Statistiken',
    'Both Teams to Score': 'Beide Teams treffen',
    'Detailed Statistics and Elite Analysis': 'Detaillierte Statistiken und Elite-Analyse',
    'Advanced statistics and detailed analysis for the %(league_name)s (%(country)s) league, %(year)s season. Explore in-depth information about corner averages, distribution of yellow and red cards per game, team discipline, volume of shots, and the exact moment goals happen throughout the 90 minutes.': 'Erweiterte Statistiken und detaillierte Analysen für die Liga %(league_name)s (%(country)s), Saison %(year)s. Entdecken Sie detaillierte Informationen über Ecken-Durchschnitte, Verteilung von gelben und roten Karten pro Spiel, Teamdisziplin, Schussvolumen und den genauen Zeitpunkt, an dem Tore innerhalb der 90 Minuten erzielt werden.',
    'So far, the overall championship average records %(avg_corners)s corners taken per match and a disciplinary average of %(avg_yellow)s yellow cards received per game. This data provides a complete overview of the tactical behavior trends and game intensity of each team in the competition.': 'Bisher verzeichnet der Gesamtdurchschnitt der Meisterschaft %(avg_corners)s Ecken pro Spiel und einen Disziplinarschnitt de %(avg_yellow)s erhaltenen gelben Karten pro Spiel. Diese Daten bieten einen vollständigen Überblick über die taktischen Verhaltenstrends und die Spielintensität jedes Teams im Wettbewerb.',
    'Goal Statistics and Over/Under Trends': 'Torstatistiken und Over/Under-Trends',
    'Complete statistics and goal analysis for the %(league_name)s (%(country)s) league. This page gathers detailed metrics on goal averages, Over/Under markets, Both Teams to Score (BTTS), Clean Sheets, and the most frequent scores to assist in your sports analysis.': 'Vollständige Statistiken und Toranalysen für die Liga %(league_name)s (%(country)s). Diese Seite sammelt detaillierte Metriken zu Tordurchschnitten, Over/Under-Märkten, Beide Teams treffen (BTTS), Spielen ohne Gegentor und den häufigsten Ergebnissen, um Sie bei Ihrer Sportanalyse zu unterstützen.',
    'The current season of the competition records a general average of %(avg_goals)s goals per game. In terms of market patterns, %(over15)s%% of matches exceeded the 1.5 goal mark and %(over25)s%% recorded more than 2.5 goals. The Both Teams to Score (BTTS) rate is at %(btts)s%%, while the percentage of games where at least one team did not concede any goals (Clean Sheet) is %(cs)s%%.': 'Die aktuelle Saison des Wettbewerbs verzeichnet einen Gesamtdurchschnitt von %(avg_goals)s Toren pro Spiel. In Bezug auf die Marktmuster übertrafen %(over15)s%% der Spiele die 1,5-Tore-Marke und %(over25)s%% verzeichneten mehr als 2,5 Tore. Die Beide-Teams-treffen-Quote (BTTS) liegt bei %(btts)s%%, während der Prozentsatz der Spiele, in denen mindestens ein Team kein Gegentor kassierte (Clean Sheet), bei %(cs)s%% liegt.'
    ,'Estatísticas completas e previsões detalhadas para a partida entre': 'Vollständige Statistiken und detaillierte Prognosen für das Spiel zwischen'
    ,'e': 'und'
    ,'válida pela': 'gültig für die'
    ,'Analise as probabilidades de Ambas Marcam (BTTS), Mais de 2.5 Gols, cantos, cartões e histórico de confrontos diretos (H2H) para apoiar suas análises e palpites esportivos baseados em dados.': 'Analysieren Sie die Wahrscheinlichkeiten für Beide treffen (BTTS), Über 2,5 Tore, Ecken, Karten und den direkten Vergleich (H2H), um Ihre datenbasierten Sportanalysen und Wetten zu unterstützen.'
    ,'Gols & Tempos': 'Tore & Halbzeiten'
    ,'Escanteios': 'Ecken'
    ,'Cartões': 'Karten'
    ,'Chutes': 'Schüsse'
    ,'Especiais & Combos': 'Spezialwetten & Kombis'
    ,'Ambas Marcam Detalhado': 'Beide treffen Detailliert'
    ,'Faixa de Gols (Partida)': 'Torbereich (Spiel)'
    ,'Faixa (1º Tempo)': 'Bereich (1. Halbzeit)'
    ,'Faixa (2º Tempo)': 'Bereich (2. Halbzeit)'
    ,'Margem de Vitória Exata': 'Genaue Gewinnspanne'
    ,'por 1 gol': 'mit 1 Tor'
    ,'por 2 gols': 'mit 2 Toren'
    ,'por 3+ gols': 'mit 3+ Toren'
    ,'Empate com gols': 'Unentschieden mit Toren'
    ,'Empate sem gols (0-0)': 'Torloses Unentschieden (0-0)'
    ,'Metades & Tempos': 'Hälften & Spielzeiten'
    ,'Mais gols no 1º Tempo': 'Mehr Tore in der 1. Halbzeit'
    ,'Mais gols no 2º Tempo': 'Mehr Tore in der 2. Halbzeit'
    ,'Metades com gols iguais': 'Gleich viele Tore in beiden Hälften'
    ,'Marcar em Ambos os Tempos': 'Treffen in beiden Halbzeiten'
    ,'Marcar Ambos Tempos': 'In beiden Hälften treffen'
    ,'Marcar pelo menos Um': 'Mindestens eine treffen'
    ,'Intervalo / Fim do Jogo': 'Halbzeit / Endstand'
    ,'Resultado 1º Tempo': 'Ergebnis 1. Halbzeit'
    ,'Vence HT': 'Führt zur Halbzeit'
    ,'Empate HT': 'Unentschieden zur Halbzeit'
    ,'Vencedor + Ambos Marcam': 'Sieger + Beide treffen'
    ,'Sim': 'Ja'
    ,'Empate': 'Unentschieden'
    ,'Chance Dupla + Faixa de Gols': 'Doppelte Chance + Torbereich'
    ,'Gols': 'Tore'
    ,'Handicap Asiático & Europeu': 'Asiatisches & Europäisches Handicap'
    ,'Empate Anula Aposta (Draw No Bet)': 'Unentschieden keine Wette (Draw No Bet)'
    ,'Match Winner (Escanteios)': 'Spielsieger (Ecken)'
    ,'Mais Escanteios': 'Mehr Ecken'
    ,'Empate de Escanteios': 'Ecken-Unentschieden'
    ,'Handicap de Escanteios': 'Ecken-Handicap'
    ,'This game has a <strong>Base of %(base)s corners</strong>, indicating high offensive volume. With an Over 8.5 prob. at %(prob)s%%, the scenario is ideal for seeking "Over 8.5 or 9.5" corner markets.': 'Dieses Spiel hat eine <strong>Basis von %(base)s Ecken</strong>, was auf ein hohes Offensivvolumen hindeutet. Mit einer Über 8,5-Wahrscheinlichkeit von %(prob)s%% ist das Szenario ideal für die Suche nach Eckenmärkten „Über 8,5 oder 9,5“.'
    ,'The base of %(base)s suggests moderate volume. The best strategy here is to look for safety markets like "Over 7.5" or wait for "Live" for better odds.': 'Die Basis von %(base)s deutet auf ein moderates Volumen hin. Die beste Strategie hierbei ist die Suche nach Sicherheitsmärkten wie „Über 7,5“ oder das Warten auf „Live“ für bessere Quoten.'
    ,'Game with a tendency for low lateral volume (Base %(base)s). Be cautious with Over bets; the "Under" market or specific corners by time may be more profitable.': 'Spiel mit Tendenz zu geringem Eckenvolumen (Basis %(base)s). Seien Sie vorsichtig mit Über-Wetten; der „Unter“-Markt oder bestimmte Ecken nach Zeit könnten profitabler sein.'
    ,'Winner & Handicap (Cartões)': 'Sieger & Handicap (Karten)'
    ,'Mais Cartões': 'Mehr Karten'
    ,'Empate de Cartões': 'Karten-Unentschieden'
    ,'Handicap': 'Handicap'
    ,'With an average of <strong>%(fouls)s fouls</strong>, we expect a tense game with many stops. The chance of cards (currently %(cards)s yellows/game) is high.': 'Mit durchschnittlich <strong>%(fouls)s Fouls</strong> erwarten wir ein spannungsgeladenes Spiel mit vielen Unterbrechungen. Die Wahrscheinlichkeit für Karten (aktuell %(cards)s Gelbe Karten/Spiel) ist hoch.'
    ,'Game with a tendency to be more fluid (only %(fouls)s fouls on average). The "Under Cards" or "Less than 4.5" market could be a good choice if the referee is not strict.': 'Das Spiel tendiert dazu, flüssiger zu sein (durchschnittlich nur %(fouls)s Fouls). Der Markt „Unter Karten“ oder „Weniger als 4,5“ könnte eine gute Wahl sein, wenn der Schiedsrichter nicht streng ist.'
    ,'Total de Chutes (Over/Under)': 'Torschüsse insgesamt (Über/Unter)'
    ,'Chutes ao Gol (Over/Under)': 'Schüsse aufs Tor (Über/Unter)'
    ,'Over 6.5 Chutes no Alvo': 'Über 6.5 Schüsse aufs Tor'
    ,'Over 7.5 Chutes no Alvo': 'Über 7.5 Schüsse aufs Tor'
    ,'Over 8.5 Chutes no Alvo': 'Über 8.5 Schüsse aufs Tor'
    ,'Over 9.5 Chutes no Alvo': 'Über 9.5 Schüsse aufs Tor'
    ,'Mais Chutes': 'Mehr Schüsse'
    ,'Match Winner (Chutes no Alvo)': 'Spielsieger (Schüsse aufs Tor)'
    ,'Mais no Alvo': 'Mehr aufs Tor'
    ,'Linhas Individuais por Time': 'Individuelle Teamlinien'
    ,'Both teams have accuracy above 30% on target. This is a very strong signal for the <strong>"Both Teams to Score: Yes"</strong> or "Over 1.5/2.5 Goals" market.': 'Beide Teams haben eine Genauigkeit von über 30 %% auf das Tor. Dies ist ein sehr starkes Signal für den Markt <strong>„Beide Teams treffen: Ja“</strong> oder „Über 1,5/2,5 Tore“.'
    ,'Only one of the teams is being lethal in finishing. Consider betting on the "Team Goals" market for the one with higher accuracy.': 'Nur eines der Teams agiert im Abschluss absolut treffsicher. Erwägen Sie eine Wette auf den Markt „Teamtore“ für das Team mit der höheren Genauigkeit.'
    ,'Both teams are struggling with finishing (Accuracy below 30%). Game with a tendency for few goals, ideal for analyzing the "Under" market.': 'Beide Teams tun sich im Abschluss schwer (Genauigkeit unter 30 %%). Spiel mit einer Tendenz zu wenigen Toren, ideal für die Analyse des „Unter“-Marktes.'
    ,'Strong': 'Stark'
    ,'Average': 'Durchschnittlich'
    ,'Weak': 'Schwach'
    ,'SMART LAY BETS (EXCHANGE)': 'SMART LAY BETS (EXCHANGE)'
    ,'Betting <strong>AGAINST</strong> these outcomes has a high statistical probability of success based on recent data.': 'Wetten <strong>GEGEN</strong> diese Ergebnisse haben basierend auf jüngsten Daten eine hohe statistische Erfolgswahrscheinlichkeit.'
    ,'Success Chance': 'Erfolgschance'
    ,'My Profile': 'Mein Profil'
    ,'Sign Out': 'Abmelden'
    ,'Login': 'Anmelden'
    ,'We use cookies to personalize content and ads, provide social media features, and analyze our traffic. By continuing to use our site, you accept our use of cookies.': 'Wir verwenden Cookies, um Inhalte und Anzeigen zu personalisieren, Funktionen für soziale Medien anzubieten und unseren Datenverkehr zu analysieren. Durch die weitere Nutzung unserer Website akzeptieren Sie unsere Verwendung von Cookies.'
    ,'Learn more': 'Mehr erfahren'
    ,'Accept': 'Akzeptieren'
    ,'All rights reserved. Professional statistics for analysts.': 'Alle Rechte vorbehalten. Professionelle Statistiken für Analysten.'
    ,'StatsFut - Advanced football statistics, pre-match analysis, Over/Under, BTTS and direct confrontations of the world\'s main leagues.': 'StatsFut - Detaillierte Fußballstatistiken, Pre-Match-Analysen, Over/Under, BTTS und direkte Duelle der wichtigsten Ligen der Welt.'
    ,'Explore advanced football statistics, pre-match analysis, Over/Under predictions and head-to-head data for the world\'s top leagues. StatsFut - Your data-driven edge.': 'Erkunden Sie detaillierte Fußballstatistiken, Pre-Match-Analysen, Over/Under-Prognosen und Head-to-Head-Daten für die weltbesten Ligen. StatsFut - Ihr datenbasierter Vorteil.'
    ,'TIMELINE': 'ZEITLEISTE'
    ,'MATCH STATS': 'SPIELSTATISTIKEN'
    ,'No goal events recorded': 'Keine Torereignisse aufgezeichnet'
    ,'Corner Kicks': 'Eckbälle'
    ,'Total Shots': 'Schüsse insgesamt'
    ,'Yellow Cards': 'Gelbe Karten'
    ,'Current Streaks & Sequences': 'Aktuelle Serien & Sequenzen'
    ,'CURRENT SEQUENCES': 'AKTUELLE SEQUENZEN'
    ,'Consecutive wins': 'Siege in Folge'
    ,'Consecutive draws': 'Unentschieden in Folge'
    ,'Consecutive defeats': 'Niederlagen in Folge'
    ,'No win': 'Kein Sieg'
    ,'No draw': 'Kein Unentschieden'
    ,'No defeat': 'Keine Niederlage'
    ,'1 goal scored or more': '1 oder mehr Tore erzielt'
    ,'1 goal conceded or more': '1 oder mehr Gegentore kassiert'
    ,'No goal scored': 'Kein Tor erzielt'
    ,'No goal conceded': 'Kein Gegentor kassiert'
    ,'GF+GA over 2.5': 'Tore insgesamt über 2.5'
    ,'GF+GA under 2.5': 'Tore insgesamt unter 2.5'
    ,'Scored at least twice': 'Mindestens zwei Tore erzielt'
    ,'Current Sequences table': 'Tabelle Aktuelle Sequenzen'
    ,'Historical statistics': 'Historische Statistiken'
    ,'(current season vs completed previous season)': '(aktuelle Saison vs. abgeschlossene Vorsaison)'
    ,'Pld': 'Sp'
    ,'Avg Pts': 'Pkt Ø'
    ,'Avg GF': 'Tore Ø'
    ,'Avg GA': 'Gegentore Ø'
    ,'Username': 'Benutzername'
    ,'Email': 'E-Mail-Adresse'
    ,'Password': 'Passwort'
    ,'Confirm Password': 'Passwort bestätigen'
    ,'Welcome Back': 'Willkommen zurück'
    ,'Sign in to access your premium stats': 'Melden Sie sich an, um auf Ihre Premium-Statistiken zuzugreifen'
    ,'Invalid username or password. Please try again.': 'Ungültiger Benutzername oder Passwort. Bitte versuchen Sie es erneut.'
    ,'Create Account': 'Konto erstellen'
    ,'Already have an account?': 'Haben Sie bereits ein Konto?'
    ,'Join StatsFut': 'Registrieren bei StatsFut'
    ,'Create your account and unlock advanced analytics': 'Erstellen Sie Ihr Konto und schalten Sie Premium-Analysen frei'
    ,'Letters, digits and @/./+/-/_ only.': 'Nur Buchstaben, Ziffern und @/./+/-/_ .'
    ,'At least 8 characters.': 'Mindestens 8 Zeichen.'
    ,'Don\'t have an account?': 'Haben Sie noch kein Konto?'
    ,'Odd Justa': 'Faire Quote'
    ,'Ambas Equipes Marcam (BTTS)': 'Beide Teams treffen (BTTS)'
    ,'Recomendado': 'Empfohlen'
    ,'Linha Principal (2.5)': 'Hauptlinie (2.5)'
    ,'Seguro': 'Sicher'
    ,'1 a 2 Gols': '1 bis 2 Tore'
    ,'2 a 3 Gols': '2 bis 3 Tore'
    ,'Base do Jogo': 'Spiel-Basis'
    ,'Best Pick': 'Beste Wahl'
    ,'Red Cards Avg:': 'Rote Karten (Schnitt):'
    ,'per game': 'pro Spiel'
    ,'Probabilidades Over Cartões': 'Karten Over Wahrscheinlichkeiten'
    ,'Total de Chutes (Over)': 'Schüsse Gesamt (Over)'
    ,'Chutes no Alvo': 'Schüsse aufs Tor'
    ,'Alvo': 'aufs Tor'
    ,'no Alvo': 'aufs Tor'
    ,'Chutes': 'Schüsse'
}

def fix_and_translate_po(filepath, translations):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Normalize line endings to LF
    content = content.replace('\r\n', '\n')
    
    # Split entries by double newline
    entries = content.split('\n\n')
    new_entries = []
    
    for entry in entries:
        if not entry.strip():
            new_entries.append(entry)
            continue
        
        lines = entry.split('\n')
        
        # Parse msgid
        msgid_lines = []
        msgid_started = False
        msgid_start_idx = -1
        
        for idx, line in enumerate(lines):
            if line.startswith('msgid "'):
                msgid_started = True
                msgid_start_idx = idx
                match = re.search(r'^msgid "(.*)"$', line)
                if match:
                    msgid_lines.append(match.group(1))
            elif msgid_started:
                if line.startswith('msgstr') or line.startswith('#'):
                    msgid_started = False
                    break
                match = re.search(r'^"(.*)"$', line)
                if match:
                    msgid_lines.append(match.group(1))
        
        if msgid_start_idx == -1:
            new_entries.append(entry)
            continue
            
        full_msgid = "".join(msgid_lines)
        
        # Find msgstr
        msgstr_start_idx = -1
        for idx, line in enumerate(lines):
            if line.startswith('msgstr'):
                msgstr_start_idx = idx
                break
        
        if msgstr_start_idx == -1:
            new_entries.append(entry)
            continue
            
        is_updated = False
        if full_msgid in translations:
            translation = translations[full_msgid]
            # Replace msgstr and any subsequent string lines in this entry with single msgstr
            lines = lines[:msgstr_start_idx] + [f'msgstr "{translation}"']
            is_updated = True
        else:
            # Check if there is an existing translation
            msgstr_lines = []
            msgstr_started = False
            for idx, line in enumerate(lines[msgstr_start_idx:], start=msgstr_start_idx):
                if line.startswith('msgstr "'):
                    msgstr_started = True
                    match = re.search(r'^msgstr "(.*)"$', line)
                    if match:
                        msgstr_lines.append(match.group(1))
                elif msgstr_started:
                    match = re.search(r'^"(.*)"$', line)
                    if match:
                        msgstr_lines.append(match.group(1))
                    else:
                        break
            
            full_msgstr = "".join(msgstr_lines)
            if full_msgstr:
                is_updated = True
        
        # If it is translated (newly or previously), clean fuzzy flags and previous msgids
        if is_updated:
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                # Remove fuzzy flags
                if stripped == '#, fuzzy' or stripped.startswith('#, fuzzy,'):
                    continue
                # Remove previous msgid reference comments
                if stripped.startswith('#|'):
                    continue
                cleaned_lines.append(line)
            lines = cleaned_lines
            
        new_entries.append("\n".join(lines))
        
    new_content = "\n\n".join(new_entries)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Processed and cleaned fuzzy flags for: {filepath}")

# Process Spanish and German
fix_and_translate_po('locale/es/LC_MESSAGES/django.po', translations_es)
fix_and_translate_po('locale/de/LC_MESSAGES/django.po', translations_de)

fix_and_translate_po('locale/en/LC_MESSAGES/django.po', translations_en)

# Process Portuguese to prevent falling back to English (since English is default_language)
translations_pt = {
    'Sobre o': 'Sobre o',
    'O %(team_name)s é um clube de futebol profissional disputando a %(league_name)s em %(country)s.': 'O %(team_name)s é um clube de futebol profissional disputando a %(league_name)s em %(country)s.',
    'Na temporada atual, a equipe ocupa a <strong>%(pos)sª</strong> posição na tabela de classificação, somando um total de <strong>%(pts)s</strong> pontos.': 'Na temporada atual, a equipe ocupa a <strong>%(pos)sª</strong> posição na tabela de classificação, somando um total de <strong>%(pts)s</strong> pontos.',
    'No StatsFut, você acompanha os placares ao vivo do %(team_name)s, resultados detalhados, estatísticas de posse de bola, gols, cartões, escanteios, escalações e o calendário completo da temporada.': 'No StatsFut, você acompanha os placares ao vivo do %(team_name)s, resultados detalhados, estatísticas de posse de bola, gols, cartões, escanteios, escalações e o calendário completo da temporada.',
    'Desempenho Geral': 'Desempenho Geral',
    'Média de <strong>%(avg_gf)s</strong> gols marcados e <strong>%(avg_ga)s</strong> sofridos por partida.': 'Média de <strong>%(avg_gf)s</strong> gols marcados e <strong>%(avg_ga)s</strong> sofridos por partida.',
    'Ambas as equipes marcaram (BTTS) em <strong>%(btts)s%%</strong> dos jogos do clube.': 'Ambas as equipes marcaram (BTTS) em <strong>%(btts)s%%</strong> dos jogos do clube.',
    'O artilheiro do elenco nesta temporada é <strong>%(name)s</strong> com <strong>%(goals)s</strong> gols marcados.': 'O artilheiro do elenco nesta temporada é <strong>%(name)s</strong> com <strong>%(goals)s</strong> gols marcados.',
    'Placares ao vivo, jogadores, programação da temporada e resultados de hoje do <strong>%(team_name)s</strong> estão disponíveis no StatsFut.': 'Placares ao vivo, jogadores, programação da temporada e resultados de hoje do <strong>%(team_name)s</strong> estão disponíveis no StatsFut.',
    'Próxima partida do': 'Próxima partida do',
    'O %(team_name)s jogará a próxima partida contra o <strong>%(opp)s</strong> no dia <strong>%(date)s</strong> pela <strong>%(league)s</strong>.': 'O %(team_name)s jogará a próxima partida contra o <strong>%(opp)s</strong> no dia <strong>%(date)s</strong> pela <strong>%(league)s</strong>.',
    'Partida anterior do': 'Partida anterior do',
    'O jogo anterior do %(team_name)s foi contra o <strong>%(opp)s</strong> pela <strong>%(league)s</strong>, terminando com o placar de <strong>%(score)s</strong>.': 'O jogo anterior do %(team_name)s foi contra o <strong>%(opp)s</strong> pela <strong>%(league)s</strong>, terminando com o placar de <strong>%(score)s</strong>.',
    'O <strong>%(team_name)s</strong> saiu vencedor desse confronto.': 'O <strong>%(team_name)s</strong> saiu vencedor desse confronto.',
    'A equipe acabou sendo derrotada.': 'A equipe acabou sendo derrotada.',
    'A partida terminou empatada.': 'A partida terminou empatada.',
    'Gráfico de desempenho e forma': 'Gráfico de desempenho e forma',
    'O gráfico de desempenho e forma do <strong>%(team_name)s</strong> é um algoritmo exclusivo do StatsFut que geramos a partir das últimas partidas, estatísticas de gols, finalizações e escanteios. Ele ajuda a entender a tendência atual da equipe e a projetar os próximos confrontos.': 'O gráfico de desempenho e forma do <strong>%(team_name)s</strong> é um algoritmo exclusivo do StatsFut que geramos a partir das últimas partidas, estatísticas de gols, finalizações e escanteios. Ele ajuda a entender a tendência atual da equipe e a projetar os próximos confrontos.',
    'Jogadores atuais do': 'Jogadores atuais do',
    'Elenco': 'Elenco',
    'anos': 'anos',
    'About Us': 'Sobre Nós',
    'About StatsFut': 'Sobre o StatsFut',
    'Our Mission': 'Nossa Missão',
    'StatsFut was born with the goal of transforming complex football data into clear, actionable insights for fans, bettors, and analysts. We believe that high-quality statistical information should be accessible, fast, and visually intuitive.': 'O StatsFut nasceu com o objetivo de transformar dados complexos de futebol em insights claros e acionáveis para torcedores, apostadores e analistas. Acreditamos que informações estatísticas de alta qualidade devem ser acessíveis, rápidas e visualmente intuitivas.',
    'Technology and Precision': 'Tecnologia e Precisão',
    'We use cutting-edge technologies to process thousands of events in real-time. Our platform integrates data from various global sources to provide a 360º view of every league, team, and matchup. We focus on advanced metrics that go beyond the scoreline, such as goal probabilities, corner trends, and head-to-head (H2H) analysis.': 'Utilizamos tecnologias de ponta para processar milhares de eventos em tempo real. Nossa plataforma integra dados de várias fontes globais para fornecer uma visão de 360º de cada liga, time e confronto. Focamos em métricas avançadas que vão além do placar, como probabilidades de gols, tendências de escanteios e análises de confronto direto (H2H).',
    'Why StatsFut?': 'Por que o StatsFut?',
    'In a sea of information, StatsFut stands out for its premium interface and data curation. We don\'t just show numbers; we organize them so you can make smarter decisions, whether to follow your favorite team or conduct professional analysis.': 'Em um mar de informações, o StatsFut se destaca por sua interface premium e curadoria de dados. Não mostramos apenas números; nós os organizamos para que você possa tomar decisões mais inteligentes, seja para acompanhar seu time favorito ou realizar análises profissionais.',
    'Constantly Evolving': 'Em Constante Evolução',
    'We are in an expansion phase, adding new leagues and predictive analysis tools regularly. StatsFut is made by data enthusiasts for football enthusiasts.': 'Estamos em fase de expansão, adicionando novas ligas e ferramentas de análise preditiva regularmente. O StatsFut é feito por entusiastas de dados para entusiastas de futebol.',
    'Last Updated: May 12, 2026': 'Última Atualização: 12 de maio de 2026',
    '1. Introduction': '1. Introdução',
    'Welcome to StatsFut. Your privacy is of extreme importance to us. This Privacy Policy explains how we collect, use, protect, and handle your information when using our website (statsfut.com).': 'Bem-vindo ao StatsFut. Sua privacidade é de extrema importância para nós. Esta Política de Privacidade explica como coletamos, usamos, protegemos e tratamos suas informações ao usar nosso site (statsfut.com).',
    '2. Information Collection': '2. Coleta de Informações',
    'We do not require registration to view public statistics. However, we collect basic information automatically through log files and cookies to improve your experience, such as:': 'Não exigimos registro para visualizar estatísticas públicas. No entanto, coletamos informações básicas automaticamente por meio de arquivos de log e cookies para melhorar sua experiência, tais como:',
    'IP Address': 'Endereço IP',
    'Browser type': 'Tipo de navegador',
    'Pages visited': 'Páginas visitadas',
    'Time spent on the site': 'Tempo gasto no site',
    '3. Cookies and Advertising (Google AdSense)': '3. Cookies e Publicidade (Google AdSense)',
    'We use cookies to provide personalized content and ads. Google, as a third-party vendor, uses cookies (such as the DART cookie) to serve ads based on your visits to our and other sites on the internet.': 'Usamos cookies para fornecer conteúdo e anúncios personalizados. O Google, como fornecedor terceirizado, usa cookies (como o cookie DART) para veicular anúncios com base em suas visitas ao nosso e a outros sites na internet.',
    'Users may opt-out of the use of the DART cookie by visiting the Google Ad and Content Network Privacy Policy.': 'Os usuários podem optar por não usar o cookie DART visitando a Política de Privacidade da rede de anúncios e conteúdo do Google.',
    '4. Use of Information': '4. Uso das Informações',
    'The information collected is used exclusively for:': 'As informações coletadas são usadas exclusivamente para:',
    'Technical maintenance and improvement of the site.': 'Manutenção técnica e melhoria do site.',
    'Traffic analysis (Google Analytics).': 'Análise de tráfego (Google Analytics).',
    'Ad personalization via advertising networks.': 'Personalização de anúncios por meio de redes de publicidade.',
    '5. Security': '5. Segurança',
    'We employ industry-standard security measures to protect information processed on our site against unauthorized access, alteration, or destruction.': 'Empregamos medidas de segurança padrão da indústria para proteger as informações processadas em nosso site contra acesso não autorizado, alteração ou destruição.',
    '6. Contact': '6. Contato',
    'If you have any questions about this Privacy Policy, please contact us through our official channels.': 'Se você tiver alguma dúvida sobre esta Política de Privacidade, entre em contato conosco através dos nossos canais oficiais.',
    '1. Acceptance of Terms': '1. Aceitação dos Termos',
    'By accessing and using the StatsFut website (statsfut.com), you agree to comply with and be bound by the following terms and conditions of use. If you do not agree with any part of these terms, you must not use our website.': 'Ao acessar e usar o site StatsFut (statsfut.com), você concorda em cumprir e ser regido pelos seguintes termos e condições de uso. Se você não concordar com qualquer parte destes termos, não deverá usar nosso site.',
    '3. Disclaimer': '3. Isenção de Responsabilidade',
    'While we strive to ensure data accuracy, StatsFut does not guarantee that the information is free of errors or omissions. We are not responsible for financial losses or decisions made based on the information contained on this site. Football is unpredictable, and past statistics do not guarantee future results.': 'Embora nos esforcemos para garantir a precisão dos dados, o StatsFut não garante que as informações estejam livres de erros ou omissões. Não nos responsabilizamos por perdas financeiras ou decisões tomadas com base nas informações contidas neste site. O futebol é imprevisível e estatísticas passadas não garantem resultados futuros.',
    '4. Intellectual Property': '4. Propriedade Intelectual',
    'The design, layout, logos, and original texts of StatsFut are intellectual property protected by copyright laws. Unauthorized reproduction of material from this site is prohibited.': 'O design, layout, logotipos e textos originais do StatsFut são propriedade intelectual protegida pelas leis de direitos autorais. A reprodução não autorizada do material deste site é proibida.',
    '5. Third-Party Links': '5. Links de Terceiros',
    'Our site may contain links to third-party websites (such as advertisers or partners). We have no control over the content or privacy practices of those sites and assume no responsibility for them.': 'Nosso site pode conter links para sites de terceiros (como anunciantes ou parceiros). Não temos controle sobre o conteúdo ou práticas de privacidade desses sites e não assumimos qualquer responsabilidade por eles.',
    '6. Changes to Terms': '6. Alterações nos Termos',
    'StatsFut reserves the right to modify these terms at any time without prior notice. We recommend periodic review of this page.': 'O StatsFut reserva-se o direito de modificar estes termos a qualquer momento, sem aviso prévio. Recomendamos a revisão periódica desta página.',
    'Get in Touch': 'Entre em Contato',
    'Have questions about our data or suggestions for new features? We\'d love to hear from you.': 'Tem dúvidas sobre nossos dados ou sugestões de novos recursos? Adoraríamos ouvir você.',
    'For general inquiries and support:': 'Para dúvidas gerais e suporte:',
    'For advertising and partnerships:': 'Para publicidade e parcerias:',
    'Our Response Time': 'Nosso Tempo de Resposta',
    'We typically respond to all inquiries within 24-48 business hours. Thank you for your patience.': 'Normalmente respondemos a todas as dúvidas em até 24-48 horas úteis. Agradecemos a sua paciência.',
    'Score': 'Placar',
    'Count': 'Quantidade',
    'Team': 'Time',
    'GP': 'GP',
    'Pts': 'Pts',
    'Rank': 'Pos',
    'Points earned in the last 8 matches': 'Pontos conquistados nos últimos 8 jogos',
    'Total': 'Total',
    'Last 8': 'Últimos 8',
    'Home': 'Casa',
    'Away': 'Fora',
    'Avg': 'Média',
    'BTS': 'AM',
    'CS': 'SG',
    'FTS': 'FM',
    'WTN': 'VSS',
    'LTN': 'PSS',
    'Games Played': 'Jogos Disputados',
    'Average Total Goals': 'Média Total de Gols',
    'Both Teams Scored': 'Ambas as Equipes Marcaram',
    'Clean Sheets': 'Jogos Sem Sofrer Gols',
    'Failed to Score': 'Jogos Sem Marcar Gols',
    'Win to Nil': 'Vencer Sem Sofrer Gols',
    'Lose to Nil': 'Perder Sem Marcar Gols',
    'League Average': 'Média da Liga',
    'Half-Time Stats': 'Estatísticas do Primeiro Tempo',
    'Both Teams to Score': 'Ambas as Equipes Marcam',
    'Detailed Statistics and Elite Analysis': 'Estatísticas Detalhadas e Análise Elite',
    'Advanced statistics and detailed analysis for the %(league_name)s (%(country)s) league, %(year)s season. Explore in-depth information about corner averages, distribution of yellow and red cards per game, team discipline, volume of shots, and the exact moment goals happen throughout the 90 minutes.': 'Estatísticas avançadas e análise detalhada da liga %(league_name)s (%(country)s), temporada de %(year)s. Explore informações detalhadas sobre médias de escanteios, distribuição de cartões amarelos e vermelhos por jogo, disciplina da equipe, volume de finalizações e o momento exato em que os gols acontecem ao longo dos 90 minutos.',
    'So far, the overall championship average records %(avg_corners)s corners taken per match and a disciplinary average of %(avg_yellow)s yellow cards received per game. This data provides a complete overview of the tactical behavior trends and game intensity of each team in the competition.': 'Até o momento, a média geral do campeonato registra %(avg_corners)s escanteios batidos por partida e uma média disciplinar de %(avg_yellow)s cartões amarelos recebidos por jogo. Esses dados fornecem uma visão completa das tendências de comportamento tático e intensidade de jogo de cada equipe na competição.',
    'Goal Statistics and Over/Under Trends': 'Estatísticas de Gols e Tendências de Over/Under',
    'Complete statistics and goal analysis for the %(league_name)s (%(country)s) league. This page gathers detailed metrics on goal averages, Over/Under markets, Both Teams to Score (BTTS), Clean Sheets, and the most frequent scores to assist in your sports analysis.': 'Estatísticas completas e análise de gols da liga %(league_name)s (%(country)s). Esta página reúne métricas detalhadas sobre médias de gols, mercados Over/Under, Ambas as Equipes Marcam (BTTS), Jogos Sem Sofrer Gols (Clean Sheet) e os placares mais frequentes para auxiliar em sua análise esportiva.',
    'The current season of the competition records a general average of %(avg_goals)s goals per game. In terms of market patterns, %(over15)s%% of matches exceeded the 1.5 goal mark and %(over25)s%% recorded more than 2.5 goals. The Both Teams to Score (BTTS) rate is at %(btts)s%%, while the percentage of games where at least one team did not concede any goals (Clean Sheet) is %(cs)s%%.': 'A temporada atual da competição registra uma média geral de %(avg_goals)s gols por jogo. Em termos de padrões de mercado, %(over15)s%% das partidas superaram a linha de 1.5 gols e %(over25)s%% registraram mais de 2.5 gols. A taxa de Ambas as Equipes Marcam (BTTS) está em %(btts)s%%, enquanto a porcentagem de jogos onde pelo menos uma equipe não sofreu gols (Clean Sheet) é de %(cs)s%%.'
    ,'Estatísticas completas e previsões detalhadas para a partida entre': 'Estatísticas completas e previsões detalhadas para a partida entre'
    ,'e': 'e'
    ,'válida pela': 'válida pela'
    ,'Analise as probabilidades de Ambas Marcam (BTTS), Mais de 2.5 Gols, cantos, cartões e histórico de confrontos diretos (H2H) para apoiar suas análises e palpites esportivos baseados em dados.': 'Analise as probabilidades de Ambas Marcam (BTTS), Mais de 2.5 Gols, cantos, cartões e histórico de confrontos diretos (H2H) para apoiar suas análises e palpites esportivos baseados em dados.'
    ,'Gols & Tempos': 'Gols & Tempos'
    ,'Escanteios': 'Escanteios'
    ,'Cartões': 'Cartões'
    ,'Chutes': 'Chutes'
    ,'Especiais & Combos': 'Especiais & Combos'
    ,'Ambas Marcam Detalhado': 'Ambas Marcam Detalhado'
    ,'Faixa de Gols (Partida)': 'Faixa de Gols (Partida)'
    ,'Faixa (1º Tempo)': 'Faixa (1º Tempo)'
    ,'Faixa (2º Tempo)': 'Faixa (2º Tempo)'
    ,'Margem de Vitória Exata': 'Margem de Vitória Exata'
    ,'por 1 gol': 'por 1 gol'
    ,'por 2 gols': 'por 2 gols'
    ,'por 3+ gols': 'por 3+ gols'
    ,'Empate com gols': 'Empate com gols'
    ,'Empate sem gols (0-0)': 'Empate sem gols (0-0)'
    ,'Metades & Tempos': 'Metades & Tempos'
    ,'Mais gols no 1º Tempo': 'Mais gols no 1º Tempo'
    ,'Mais gols no 2º Tempo': 'Mais gols no 2º Tempo'
    ,'Metades com gols iguais': 'Metades com gols iguais'
    ,'Marcar em Ambos os Tempos': 'Marcar em Ambos os Tempos'
    ,'Marcar Ambos Tempos': 'Marcar Ambos Tempos'
    ,'Marcar pelo menos Um': 'Marcar pelo menos Um'
    ,'Intervalo / Fim do Jogo': 'Intervalo / Fim do Jogo'
    ,'Resultado 1º Tempo': 'Resultado 1º Tempo'
    ,'Vence HT': 'Vence HT'
    ,'Empate HT': 'Empate HT'
    ,'Vencedor + Ambos Marcam': 'Vencedor + Ambos Marcam'
    ,'Sim': 'Sim'
    ,'Empate': 'Empate'
    ,'Chance Dupla + Faixa de Gols': 'Chance Dupla + Faixa de Gols'
    ,'Gols': 'Gols'
    ,'Handicap Asiático & Europeu': 'Handicap Asiático & Europeu'
    ,'Empate Anula Aposta (Draw No Bet)': 'Empate Anula Aposta (Draw No Bet)'
    ,'Match Winner (Escanteios)': 'Match Winner (Escanteios)'
    ,'Mais Escanteios': 'Mais Escanteios'
    ,'Empate de Escanteios': 'Empate de Escanteios'
    ,'Handicap de Escanteios': 'Handicap de Escanteios'
    ,'This game has a <strong>Base of %(base)s corners</strong>, indicating high offensive volume. With an Over 8.5 prob. at %(prob)s%%, the scenario is ideal for seeking "Over 8.5 or 9.5" corner markets.': 'This game has a <strong>Base of %(base)s corners</strong>, indicating high offensive volume. With an Over 8.5 prob. at %(prob)s%%, the scenario is ideal for seeking "Over 8.5 or 9.5" corner markets.'
    ,'The base of %(base)s suggests moderate volume. The best strategy here is to look for safety markets like "Over 7.5" or wait for "Live" for better odds.': 'The base of %(base)s suggests moderate volume. The best strategy here is to look for safety markets like "Over 7.5" or wait for "Live" for better odds.'
    ,'Game with a tendency for low lateral volume (Base %(base)s). Be cautious with Over bets; the "Under" market or specific corners by time may be more profitable.': 'Game with a tendency for low lateral volume (Base %(base)s). Be cautious with Over bets; the "Under" market or specific corners by time may be more profitable.'
    ,'Winner & Handicap (Cartões)': 'Winner & Handicap (Cartões)'
    ,'Mais Cartões': 'Mais Cartões'
    ,'Empate de Cartões': 'Empate de Cartões'
    ,'Handicap': 'Handicap'
    ,'With an average of <strong>%(fouls)s fouls</strong>, we expect a tense game with many stops. The chance of cards (currently %(cards)s yellows/game) is high.': 'With an average of <strong>%(fouls)s fouls</strong>, we expect a tense game with many stops. The chance of cards (currently %(cards)s yellows/game) is high.'
    ,'Game with a tendency to be more fluid (only %(fouls)s fouls on average). The "Under Cards" or "Less than 4.5" market could be a good choice if the referee is not strict.': 'Game with a tendency to be more fluid (only %(fouls)s fouls on average). The "Under Cards" or "Less than 4.5" market could be a good choice if the referee is not strict.'
    ,'Total de Chutes (Over/Under)': 'Total de Chutes (Over/Under)'
    ,'Chutes ao Gol (Over/Under)': 'Chutes ao Gol (Over/Under)'
    ,'Over 6.5 Chutes no Alvo': 'Over 6.5 Chutes no Alvo'
    ,'Over 7.5 Chutes no Alvo': 'Over 7.5 Chutes no Alvo'
    ,'Over 8.5 Chutes no Alvo': 'Over 8.5 Chutes no Alvo'
    ,'Over 9.5 Chutes no Alvo': 'Over 9.5 Chutes no Alvo'
    ,'Mais Chutes': 'Mais Chutes'
    ,'Match Winner (Chutes no Alvo)': 'Match Winner (Chutes no Alvo)'
    ,'Mais no Alvo': 'Mais no Alvo'
    ,'Linhas Individuais por Time': 'Linhas Individuais por Time'
    ,'Both teams have accuracy above 30% on target. This is a very strong signal for the <strong>"Both Teams to Score: Yes"</strong> or "Over 1.5/2.5 Goals" market.': 'Both teams have accuracy above 30% on target. This is a very strong signal for the <strong>"Both Teams to Score: Yes"</strong> or "Over 1.5/2.5 Goals" market.'
    ,'Only one of the teams is being lethal in finishing. Consider betting on the "Team Goals" market for the one with higher accuracy.': 'Only one of the teams is being lethal in finishing. Consider betting on the "Team Goals" market for the one with higher accuracy.'
    ,'Both teams are struggling with finishing (Accuracy below 30%). Game with a tendency for few goals, ideal for analyzing the "Under" market.': 'Both teams are struggling with finishing (Accuracy below 30%). Game with a tendency for few goals, ideal for analyzing the "Under" market.'
    ,'Strong': 'Forte'
    ,'Average': 'Regular'
    ,'Weak': 'Frágil'
    ,'SMART LAY BETS (EXCHANGE)': 'APOSTAS SMART LAY (EXCHANGE)'
    ,'Betting <strong>AGAINST</strong> these outcomes has a high statistical probability of success based on recent data.': 'Apostar <strong>CONTRA</strong> estes resultados tem uma alta probabilidade estatística de sucesso com base em dados recentes.'
    ,'Success Chance': 'Chance de Sucesso'
    ,'My Profile': 'Meu Perfil'
    ,'Sign Out': 'Sair'
    ,'Login': 'Entrar'
    ,'We use cookies to personalize content and ads, provide social media features, and analyze our traffic. By continuing to use our site, you accept our use of cookies.': 'Utilizamos cookies para personalizar conteúdo e anúncios, fornecer recursos de mídia social e analisar nosso tráfego. Ao continuar a usar nosso site, você aceita o uso de cookies.'
    ,'Learn more': 'Saiba mais'
    ,'Accept': 'Aceitar'
    ,'All rights reserved. Professional statistics for analysts.': 'Todos os direitos reservados. Estatísticas profissionais para analistas.'
    ,'StatsFut - Advanced football statistics, pre-match analysis, Over/Under, BTTS and direct confrontations of the world\'s main leagues.': 'StatsFut - Estatísticas avançadas de futebol, análises pré-jogo, Over/Under, BTTS e confrontos diretos das principais ligas do mundo.'
    ,'Explore advanced football statistics, pre-match analysis, Over/Under predictions and head-to-head data for the world\'s top leagues. StatsFut - Your data-driven edge.': 'Explore estatísticas avançadas de futebol, análises pré-jogo, previsões Over/Under e dados de confrontos diretos das principais ligas do mundo. StatsFut - Sua vantagem baseada em dados.'
    ,'TIMELINE': 'CRONOLOGIA'
    ,'MATCH STATS': 'ESTADÍSTICAS DA PARTIDA'
    ,'No goal events recorded': 'Nenhum gol registrado'
    ,'Corner Kicks': 'Escanteios'
    ,'Total Shots': 'Finalizações Totais'
    ,'Yellow Cards': 'Cartões Amarelos'
    ,'Current Streaks & Sequences': 'Sequências e Rachas Atuais'
    ,'CURRENT SEQUENCES': 'SEQUÊNCIAS ATUAIS'
    ,'Consecutive wins': 'Vitórias consecutivas'
    ,'Consecutive draws': 'Empates consecutivos'
    ,'Consecutive defeats': 'Derrotas consecutivas'
    ,'No win': 'Sem vencer'
    ,'No draw': 'Sem empatar'
    ,'No defeat': 'Sem perder'
    ,'1 goal scored or more': '1 gol marcado ou mais'
    ,'1 goal conceded or more': '1 gol sofrido ou mais'
    ,'No goal scored': 'Sem gols marcados'
    ,'No goal conceded': 'Sem gols sofridos'
    ,'GF+GA over 2.5': 'Gols Pro + Contra mais de 2.5'
    ,'GF+GA under 2.5': 'Gols Pro + Contra menos de 2.5'
    ,'Scored at least twice': 'Marcou pelo menos dois gols'
    ,'Current Sequences table': 'Tabela de Sequências Atuais'
    ,'Historical statistics': 'Estatísticas históricas'
    ,'(current season vs completed previous season)': '(temporada atual vs temporada anterior concluída)'
    ,'Pld': 'PJ'
    ,'Avg Pts': 'Média Pts'
    ,'Avg GF': 'Média GP'
    ,'Avg GA': 'Média GC'
    ,'Username': 'Usuário'
    ,'Email': 'E-mail'
    ,'Password': 'Senha'
    ,'Confirm Password': 'Confirmar Senha'
    ,'Welcome Back': 'Bem-vindo de volta'
    ,'Sign in to access your premium stats': 'Faça login para acessar suas estatísticas premium'
    ,'Invalid username or password. Please try again.': 'Usuário ou senha inválidos. Por favor, tente novamente.'
    ,'Create Account': 'Conta Gratuita'
    ,'Already have an account?': 'Já tem uma conta?'
    ,'Join StatsFut': 'Cadastrar no StatsFut'
    ,'Create your account and unlock advanced analytics': 'Crie sua conta e libere estatísticas avançadas'
    ,'Letters, digits and @/./+/-/_ only.': 'Apenas letras, números e @/./+/-/_ .'
    ,'At least 8 characters.': 'Pelo menos 8 caracteres.'
    ,'Don\'t have an account?': 'Não tem uma conta?'
    ,'Odd Justa': 'Odd Justa'
    ,'Ambas Equipes Marcam (BTTS)': 'Ambas Equipes Marcam (BTTS)'
    ,'Recomendado': 'Recomendado'
    ,'Linha Principal (2.5)': 'Linha Principal (2.5)'
    ,'Seguro': 'Seguro'
    ,'1 a 2 Gols': '1 a 2 Gols'
    ,'2 a 3 Gols': '2 a 3 Gols'
    ,'Base do Jogo': 'Base do Jogo'
    ,'Best Pick': 'Melhor Palpite'
    ,'Red Cards Avg:': 'Média de Cartões Vermelhos:'
    ,'per game': 'por jogo'
    ,'Probabilidades Over Cartões': 'Probabilidades Over Cartões'
    ,'Total de Chutes (Over)': 'Total de Chutes (Over)'
    ,'Chutes no Alvo': 'Chutes no Alvo'
    ,'Alvo': 'no Alvo'
    ,'no Alvo': 'no Alvo'
    ,'Chutes': 'Chutes'
}

fix_and_translate_po('locale/pt/LC_MESSAGES/django.po', translations_pt)
fix_and_translate_po('locale/pt_BR/LC_MESSAGES/django.po', translations_pt)
