import re

with open('matches/templates/matches/league_goals.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Try to find the exact block using regex since spacing might differ
old_seo_pattern = r'<!-- SEO Text Card \(Bottom\) -->\s*<div class="row mt-5 mb-2">.*?</div>\s*</div>\s*</div>\s*</div>'
match = re.search(old_seo_pattern, content, flags=re.DOTALL)

if not match:
    print("Could not find the SEO block in the HTML.")
    exit(1)

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
                                <p class="mb-3">
                                    {% blocktranslate with league_name=league.name %}Complete goal statistics for the <strong>{{ league_name }}</strong>. Analyze Over/Under goals trends, average goals per match, and the Both Teams to Score (BTTS) percentage. Discover which teams have the most efficient attacks, which have the best defenses (Clean Sheets), and find the best opportunities for your sports analysis in the goals markets.{% endblocktranslate %}
                                </p>
                                {% if league_avg_row %}
                                <p class="mb-0">
                                    {% blocktranslate with avg_goals=league_avg_row.avg_total|floatformat:2 over25=league_avg_row.over25_pct|floatformat:0 btts=league_avg_row.bts_pct|floatformat:0 %}Currently, the overall league average is <strong>{{ avg_goals }}</strong> goals per match. About <strong>{{ over25 }}%</strong> of the matches end with Over 2.5 goals and the Both Teams to Score (BTTS) market hits in <strong>{{ btts }}%</strong> of the games. Use this advanced data to support your predictions.{% endblocktranslate %}
                                </p>
                                {% endif %}
                            </div>

                            <!-- Estatísticas FT/HT -->
                            <div id="seo-text-ft" class="seo-text-block d-none">
                                <p class="mb-0">
                                    {% blocktranslate with league_name=league.name %}Detailed goals statistics separated by Full Time (FT), Half Time (HT) and Second Half (2H) for the <strong>{{ league_name }}</strong>. Discover the average goals scored and conceded in each stage of the match, as well as the percentages for over 0.5, 1.5, and 2.5 goals per half. Use these insights to find value in HT and 2H markets.{% endblocktranslate %}
                                </p>
                            </div>

                            <!-- Ambas as Equipes Marcam -->
                            <div id="seo-text-btts" class="seo-text-block d-none">
                                <p class="mb-0">
                                    {% blocktranslate with league_name=league.name %}Focused analysis on the Both Teams to Score (BTTS) market in the <strong>{{ league_name }}</strong>. See how often teams score and concede in the same match, whether playing at home, away, or across all matches in the season. Identify the teams with the highest BTTS trends for your sports predictions.{% endblocktranslate %}
                                </p>
                            </div>

                            <!-- Defesa e Jogos Sem Sofrer Gols -->
                            <div id="seo-text-defesa" class="seo-text-block d-none">
                                <p class="mb-0">
                                    {% blocktranslate with league_name=league.name %}Defensive statistics and Clean Sheets market for the <strong>{{ league_name }}</strong>. Find out which teams have the most solid defenses, the highest probability of not conceding goals in their matches, and the percentage of games they win to nil (Win To Nil). Essential data for defensive performance analysis.{% endblocktranslate %}
                                </p>
                            </div>

                            <!-- Tempo dos Gols -->
                            <div id="seo-text-timing" class="seo-text-block d-none">
                                <p class="mb-0">
                                    {% blocktranslate with league_name=league.name %}Advanced statistics on Goal Timings in the <strong>{{ league_name }}</strong>. Understand in which 15-minute segments teams score or concede the most goals, which teams usually score the First Goal of the match, their performance when leading at half-time, and the most common Half Time / Full Time (HT/FT) outcomes.{% endblocktranslate %}
                                </p>
                            </div>

                        </div>
                    </div>
                </div>
            </div>'''

content = content[:match.start()] + new_seo + content[match.end():]

script_add = '''
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Dynamic SEO Text based on main tabs
        const mainTabs = document.querySelectorAll('#leagueGoalsTabs button[data-bs-toggle="tab"]');
        mainTabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', function (event) {
                // Hide all SEO blocks
                document.querySelectorAll('.seo-text-block').forEach(el => el.classList.add('d-none'));
                
                // Show the active one
                const target = event.target.getAttribute('data-bs-target').replace('#', '');
                const seoBlock = document.getElementById('seo-text-' + target);
                if(seoBlock) {
                    seoBlock.classList.remove('d-none');
                }
            });
        });
    });
</script>
'''

if 'Dynamic SEO Text based on main tabs' not in content:
    # Append the script just before {% endblock %}
    block_end_idx = content.rfind('{% endblock %}')
    if block_end_idx != -1:
        content = content[:block_end_idx] + script_add + content[block_end_idx:]
    else:
        content += script_add

with open('matches/templates/matches/league_goals.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done replacing SEO blocks in HTML.')
