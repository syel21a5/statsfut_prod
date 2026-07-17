import re

with open('matches/templates/matches/league_goals.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_seo_pattern = r'<!-- SEO Text Card \(Bottom\) -->\s*<div class=\"row mt-5 mb-2\">.*?</div>\s*</div>\s*</div>\s*</div>'
match = re.search(old_seo_pattern, content, flags=re.DOTALL)

new_seo = '''<!-- SEO Text Card (Bottom) -->
            <div class="row mt-5 mb-2">
                <div class="col-12">
                    <div class="card border-0 text-white shadow-sm mb-4" style="background: #0b0f19; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 20px;">
                        <div class="card-header bg-transparent border-bottom border-white border-opacity-5 py-3">
                            <h5 class="mb-0 fw-bold text-info" id="seo-card-title">
                                <i class="fa-solid fa-chart-line me-2"></i>{% translate "Goals Analysis and Probabilities" %}: {{ league.name }}
                            </h5>
                        </div>
                        <div class="card-body px-4 pb-4 pt-4 seo-card-body" style="font-size: 0.92rem;">
                            
                            <!-- Resumo e Placares -->
                            <div id="seo-text-resumo" class="seo-text-block">
                                <p class="mb-3">{% blocktranslate with league_name=league.name %}Complete goal statistics and comprehensive match analysis for the <strong>{{ league_name }}</strong>. Explore deep data regarding Over/Under goals trends, average goals scored per match, and the frequency of Both Teams to Score (BTTS) outcomes across the entire season. Our platform provides a detailed overview of the most crucial betting markets for football fans and professional analysts alike.{% endblocktranslate %}</p>
                                <p class="mb-3">{% blocktranslate %}By analyzing the data, you can discover which teams boast the most efficient attacking forces and which rely on solid defensive setups to secure Clean Sheets. Whether you are looking for high-scoring fixtures or tight, low-scoring tactical battles, our summary tables give you the exact percentages you need to find the best opportunities in the goals markets.{% endblocktranslate %}</p>
                                {% if league_avg_row %}
                                <p class="mb-0">{% blocktranslate with avg_goals=league_avg_row.avg_total|floatformat:2 over25=league_avg_row.over25_pct|floatformat:0 btts=league_avg_row.bts_pct|floatformat:0 %}Currently, the overall league average is <strong>{{ avg_goals }}</strong> goals per match. About <strong>{{ over25 }}%</strong> of the matches end with Over 2.5 goals and the Both Teams to Score (BTTS) market hits in <strong>{{ btts }}%</strong> of the games. Use this advanced data to support your predictions.{% endblocktranslate %}</p>
                                {% endif %}
                            </div>

                            <!-- Estatísticas FT/HT -->
                            <div id="seo-text-ft" class="seo-text-block d-none">
                                <p class="mb-3">{% blocktranslate with league_name=league.name %}Detailed goals statistics separated by Full Time (FT), Half Time (HT), and Second Half (2H) segments for the <strong>{{ league_name }}</strong>. Understanding how teams perform across different halves is crucial for live betting and advanced sports analysis. Discover the average goals scored and conceded in each stage of the match to identify teams that start strong or those that dominate the final 45 minutes.{% endblocktranslate %}</p>
                                <p class="mb-3">{% blocktranslate %}Dive deeper into the percentages for over 0.5, 1.5, and 2.5 goals specifically filtered by half. Some teams might have a high overall goal average but rarely score in the first half. Our FT/HT breakdown allows you to pinpoint these precise trends and use these insights to find hidden value in Half Time (HT) and Second Half (2H) betting markets.{% endblocktranslate %}</p>
                                <p class="mb-0">{% blocktranslate with league_name=league.name %}Maximize your edge by comparing home and away performances for each team during the first and second halves. Uncover patterns that regular full-time statistics simply cannot reveal, giving you a comprehensive tactical view of how matches unfold in the <strong>{{ league_name }}</strong>.{% endblocktranslate %}</p>
                            </div>

                            <!-- Ambas as Equipes Marcam -->
                            <div id="seo-text-btts" class="seo-text-block d-none">
                                <p class="mb-3">{% blocktranslate with league_name=league.name %}Focused and in-depth analysis on the Both Teams to Score (BTTS) market in the <strong>{{ league_name }}</strong>. The BTTS market is one of the most popular among football analysts, and our platform tracks exactly how often teams both score and concede in the same match. Explore season-long trends to see which matchups are practically guaranteed to feature goals from both sides.{% endblocktranslate %}</p>
                                <p class="mb-3">{% blocktranslate %}See how BTTS frequencies shift when teams are playing in front of their home fans versus when they travel away. Some squads adopt highly aggressive tactics at home, leading to high-scoring end-to-end games, while others play defensively on the road. Identify the teams with the highest BTTS trends to confidently inform your sports predictions.{% endblocktranslate %}</p>
                                <p class="mb-0">{% blocktranslate with league_name=league.name %}Combine BTTS data with our Over 2.5 goals statistics to find the ultimate high-value matches. By studying the historical occurrence of both teams finding the back of the net, you can significantly improve your accuracy when evaluating goal-heavy fixtures in the <strong>{{ league_name }}</strong>.{% endblocktranslate %}</p>
                            </div>

                            <!-- Defesa e Jogos Sem Sofrer Gols -->
                            <div id="seo-text-defesa" class="seo-text-block d-none">
                                <p class="mb-3">{% blocktranslate with league_name=league.name %}Advanced defensive statistics and Clean Sheets market analysis for the <strong>{{ league_name }}</strong>. While attackers win games, defenses win championships. Find out which teams possess the most solid defensive lines and the highest probability of not conceding any goals during their domestic league matches.{% endblocktranslate %}</p>
                                <p class="mb-3">{% blocktranslate %}Track the percentage of games where teams successfully keep a Clean Sheet, as well as how often they manage to Win To Nil (win the match without conceding). These metrics are essential for defensive performance analysis and are highly valuable for bettors looking at Under goals markets or specific team clean sheet propositions.{% endblocktranslate %}</p>
                                <p class="mb-0">{% blocktranslate with league_name=league.name %}Analyze the defensive resilience of each club by splitting their performance into home and away fixtures. Discover which stadiums are true fortresses where visiting teams struggle to score, providing you with critical data for predicting low-scoring affairs in the <strong>{{ league_name }}</strong>.{% endblocktranslate %}</p>
                            </div>

                            <!-- Tempo dos Gols -->
                            <div id="seo-text-timing" class="seo-text-block d-none">
                                <p class="mb-3">{% blocktranslate with league_name=league.name %}Granular statistics on Goal Timings (Tempo dos Gols) in the <strong>{{ league_name }}</strong>. Timing is everything in football, and understanding exactly when teams are most vulnerable or dangerous can provide a massive analytical advantage. Explore our breakdown of goals scored and conceded in specific 15-minute segments throughout the match.{% endblocktranslate %}</p>
                                <p class="mb-3">{% blocktranslate %}Find out which teams consistently strike early by scoring the First Goal of the match, and analyze their performance when leading, drawing, or losing at half-time. We also provide comprehensive data on the most common Half Time / Full Time (HT/FT) outcomes, showing exactly how teams transition their momentum from the first half into the final result.{% endblocktranslate %}</p>
                                <p class="mb-0">{% blocktranslate with league_name=league.name %}Whether a team is known for late drama in the final 15 minutes (76-90') or for blitzing opponents right after kick-off (0-15'), our advanced timing data reveals the true tactical rhythm of every squad in the <strong>{{ league_name }}</strong>. Use these insights to master live betting and minute-specific goal markets.{% endblocktranslate %}</p>
                            </div>

                        </div>
                    </div>
                </div>
            </div>'''

if match:
    content = content[:match.start()] + new_seo + content[match.end():]
    with open('matches/templates/matches/league_goals.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced successfully.')
else:
    print('Pattern not found!')
