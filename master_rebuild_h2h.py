import os

os.system("git checkout matches/templates/matches/h2h_detail.html")

html_file = r'i:\GitHub\statsfut\statsfut\matches\templates\matches\h2h_detail.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Let's extract the blocks safely without backwards rfinds.

def get_block(start_marker, end_marker):
    start = content.find(start_marker)
    if start == -1: return ""
    if end_marker:
        end = content.find(end_marker, start)
        if end == -1: return ""
        return content[start:end]
    else:
        return content[start:]

# The markers in the original file:
# <!-- Matchup Header Card -->
# <!-- H2H SEO Dynamic Text -->
# <!-- MAIN GRID: Team 1 Column vs Team 2 Column -->
# <!-- Key Probabilities -->
# <!-- Middle Ad Block -->
# <div class="row g-4">\n                <!-- Comparison Stats (Total) -->
#                 <!-- Recent H2H Matches -->
#             <!-- NEW: Detailed Goals Analysis Grid -->
#             <!-- Points Per Game
#             {% if fallback_h2h %}

block_header = get_block('            <!-- Matchup Header Card -->', '            <!-- MAIN GRID: Team 1 Column vs Team 2 Column -->')

block_maingrid = get_block('            <!-- MAIN GRID: Team 1 Column vs Team 2 Column -->', '            <!-- Key Probabilities -->')

block_kp = get_block('            <!-- Key Probabilities -->', '    <!-- Middle Ad Block -->')
block_ad = get_block('    <!-- Middle Ad Block -->', '<div class="row g-4">\n                <!-- Comparison Stats (Total) -->')

# The row with 3 col-lg-4 blocks
row_3cols_start = content.find('<div class="row g-4">\n                <!-- Comparison Stats (Total) -->')
row_3cols_end = content.find('            <!-- NEW: Detailed Goals Analysis Grid -->')
row_3cols = content[row_3cols_start:row_3cols_end]

# Inside row_3cols, we have three blocks. We want to extract Comparison Stats and Home vs Away, but leave Recent H2H out.
# Or rather, we want to just replace the two `<div class="col-lg-4">` with `<div class="col-lg-6">` inside this block, and completely drop the Recent H2H part.
# The Recent H2H part starts at `                <!-- Recent H2H Matches -->`.
recent_start = row_3cols.find('                <!-- Recent H2H Matches -->')
comp_and_home_away = row_3cols[:recent_start]

# We need to change the two `col-lg-4` to `col-lg-6` in comp_and_home_away
comp_and_home_away = comp_and_home_away.replace('class="col-lg-4"', 'class="col-lg-6"')

# We must close the `<div class="row g-4">` that started at the beginning of comp_and_home_away
comp_and_home_away += '            </div>\n'

# Now block_goals and block_ppg
block_goals = get_block('            <!-- NEW: Detailed Goals Analysis Grid -->', '            <!-- Points Per Game')
block_ppg = get_block('            <!-- Points Per Game', '            {% if fallback_h2h %}')
block_fallback = get_block('            {% if fallback_h2h %}', '        </div>\n        <!-- Right Sidebar (25% Width) for Ads -->')

# Wait, `block_fallback` goes all the way to `        </div>\n        <!-- Right Sidebar`
# But `block_fallback` must not include the closing `</div>` of `col-lg-9` if we want to keep it outside, or we can just replace everything inside `col-lg-9`.

# Let's find exactly the inside of `col-lg-9`
idx_col9 = content.find('<div class="col-lg-9">') + len('<div class="col-lg-9">\n')
idx_col9_end = content.find('        <!-- Right Sidebar (25% Width) for Ads -->')
idx_col9_end = content.rfind('        </div>', 0, idx_col9_end)

# We will completely replace the inside of col-lg-9 with our newly built tabs.
tabs_nav = """
            <style>
                .premium-tabs { background: rgba(255,255,255,0.05); padding: 6px; border-radius: 12px; display: inline-flex; gap: 5px; border: 1px solid rgba(255,255,255,0.1); flex-wrap: wrap; }
                .premium-tabs .nav-link { color: #94a3b8 !important; border-radius: 8px !important; font-weight: 600; padding: 8px 16px; transition: all 0.3s; background: transparent !important; }
                .premium-tabs .nav-link:hover { color: #fff !important; background: rgba(255,255,255,0.1) !important; }
                .premium-tabs .nav-link.active { color: #fff !important; background: linear-gradient(135deg, #0ea5e9, #2563eb) !important; box-shadow: 0 4px 12px rgba(14,165,233,0.3); }
            </style>
            <ul class="nav nav-pills premium-tabs mb-4" id="h2hTabs" role="tablist">
                <li class="nav-item" role="presentation"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#frente" type="button" role="tab"><i class="fa-solid fa-handshake-angle me-2"></i>Histórico Direto</button></li>
                <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#comparacao" type="button" role="tab"><i class="fa-solid fa-scale-balanced me-2"></i>Forma e Estatísticas</button></li>
                <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#avancadas" type="button" role="tab"><i class="fa-solid fa-chart-line me-2"></i>Análise Avançada</button></li>
            </ul>
            <div class="tab-content" id="h2hTabsContent">
"""

rich_recent = """
            <div class="row g-4 mb-4 mt-1">
                <div class="col-12">
                    <div class="card border-0 bg-white bg-opacity-10 text-white shadow-sm">
                        <div class="card-header bg-transparent border-bottom border-secondary border-opacity-25 py-3">
                            <h5 class="mb-0 fw-bold text-uppercase small tracking-wide"><i class="fa-solid fa-clock-rotate-left text-info me-2"></i>{% translate "Recent H2H Matches" %}</h5>
                        </div>
                        <div class="card-body p-0">
                            <div class="table-responsive custom-scrollbar" style="max-height: 400px; overflow-y: auto;">
                                <table class="table table-dark table-hover mb-0 align-middle text-center small">
                                    <thead class="sticky-top bg-dark">
                                        <tr class="text-secondary text-uppercase">
                                            <th class="ps-4 text-start">{% translate "Date" %}</th>
                                            <th class="text-end">{% translate "Home" %}</th>
                                            <th>{% translate "Score" %}</th>
                                            <th class="text-start">{% translate "Away" %}</th>
                                            <th class="pe-4 text-end">{% translate "Action" %}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                         {% for match in matches %}
                                         <tr>
                                             <td class="ps-4 text-start text-secondary">{{ match.date|date:"d M Y" }}</td>
                                             
                                             <td class="text-end align-middle {% if match.home_score > match.away_score %}fw-bold text-white{% else %}text-secondary{% endif %}">
                                                 <div class="d-flex align-items-center justify-content-end gap-2">
                                                     <span>{{ match.home_team.name }}</span>
                                                     {% if match.home_team.logo_url %}<img src="{{ match.home_team.logo_url }}" alt="{{ match.home_team.name }}" style="width: 20px; height: 20px; object-fit: contain;">{% endif %}
                                                 </div>
                                             </td>
                                             
                                             <td class="text-center">
                                                 <span class="badge bg-dark border border-secondary border-opacity-50 px-3 py-1 fs-6">
                                                     {{ match.home_score }} - {{ match.away_score }}
                                                 </span>
                                             </td>
                                             
                                             <td class="text-start align-middle {% if match.away_score > match.home_score %}fw-bold text-white{% else %}text-secondary{% endif %}">
                                                 <div class="d-flex align-items-center justify-content-start gap-2">
                                                     {% if match.away_team.logo_url %}<img src="{{ match.away_team.logo_url }}" alt="{{ match.away_team.name }}" style="width: 20px; height: 20px; object-fit: contain;">{% endif %}
                                                     <span>{{ match.away_team.name }}</span>
                                                 </div>
                                             </td>
                                             
                                             <td class="pe-4 text-end">
                                                 <a href="{% url 'matches:match_detail_short' pk=match.id %}" class="btn btn-sm btn-success py-1 px-3 fw-bold" style="font-size: 0.75rem;"><i class="fa-solid fa-bolt me-1"></i>{% translate "Analyze" %}</a>
                                             </td>
                                         </tr>
                                         {% empty %}
                                         <tr>
                                             <td colspan="5" class="text-center py-4 text-secondary">{% translate "No recent matches." %}</td>
                                         </tr>
                                         {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
"""

cta_html = """
                    {% if next_match %}
                    <div class="row mb-4">
                        <div class="col-12">
                            <div class="card border-0 bg-info bg-opacity-10 text-white shadow-sm border border-info border-opacity-25">
                                <div class="card-body text-center p-4">
                                    <h4 class="fw-bold mb-3"><i class="fa-solid fa-lock-open text-info me-2"></i>{% translate "Unlock Full Algorithmic Analysis" %}</h4>
                                    <p class="text-secondary mb-4">{% translate "See advanced predictions, over/under probabilities, corner stats, and AI tips for the upcoming match." %}</p>
                                    <a href="{% url 'matches:match_detail' pk=next_match.pk slug=next_match.slug %}" class="btn btn-info fw-bold px-5 py-2 rounded-pill shadow">
                                        <i class="fa-solid fa-bolt me-2"></i>{% translate "View Full Analysis" %}
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endif %}
"""

aba1 = f'                <div class="tab-pane fade show active" id="frente" role="tabpanel">\n{block_header}{comp_and_home_away}{rich_recent}                </div>\n'
aba2 = f'                <div class="tab-pane fade" id="comparacao" role="tabpanel">\n{block_maingrid}{block_ppg}                </div>\n'
aba3 = f'                <div class="tab-pane fade" id="avancadas" role="tabpanel">\n{cta_html}{block_kp}{block_goals}{block_fallback}                </div>\n'

new_main_content = tabs_nav + aba1 + aba2 + aba3 + '            </div>\n'

results_target = '<div class="table-responsive">\n                                <table class="table table-dark table-hover mb-0 align-middle small">\n                                    <thead>'
results_replace = '<div class="table-responsive custom-scrollbar" style="max-height: 350px; overflow-y: auto;">\n                                <table class="table table-dark table-hover mb-0 align-middle small">\n                                    <thead class="sticky-top" style="background-color: #1a1e29; z-index: 2;">'
new_main_content = new_main_content.replace(results_target, results_replace)

final_content = content[:idx_col9] + new_main_content + content[idx_col9_end:]

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(final_content)

print("Master rebuild complete.")
