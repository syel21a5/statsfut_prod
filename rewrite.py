import re

with open('matches/templates/matches/league_detailed_stats.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add cache to load
content = re.sub(r'\{% load matches_extras %\}', '{% load matches_extras cache %}', content)

# Replace from '<!-- Custom Tabs CSS -->' down to '<!-- SEO Text Card (Bottom) -->'
start_marker = '<!-- Custom Tabs CSS -->'
end_marker = '<!-- SEO Text Card (Bottom) -->'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

# Extract the existing cards to reuse them
corners_card = re.search(r'<!-- \{\% translate \"Corners Performance Ranking\" \%\} -->(.*?)<!-- Aba 2:', content, re.DOTALL)
if corners_card:
    corners_card_html = corners_card.group(1).strip()
    corners_card_html = '\n'.join(corners_card_html.split('\n')[:-4])
else:
    print('Failed to find corners card')

goal_timing = re.search(r'<!-- Goal Timing Card -->(.*?)<div class=\"col-md-6\">', content, re.DOTALL)
if goal_timing:
    goal_timing_html = goal_timing.group(1).strip()
    goal_timing_html = '\n'.join(goal_timing_html.split('\n')[:-2])
else:
    print('Failed to find goal timing')

top_scorers = re.search(r'<!-- Top Scorers Card -->(.*?)<!-- SEO Text Card', content, re.DOTALL)
if top_scorers:
    top_scorers_html = top_scorers.group(1).strip()
    top_scorers_html = '\n'.join(top_scorers_html.split('\n')[:-5])
else:
    print('Failed to find top scorers')

cards_card_html = '''
<!-- Cards & Discipline Ranking -->
<div class="custom-card d-flex flex-column h-100">
    <div class="card-header bg-transparent border-bottom border-white border-opacity-5 p-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
        <h5 class="mb-0 text-white fw-bold d-flex align-items-center gap-2" style="font-size: 1.1rem;">
            <i class="fa-solid fa-copy text-warning"></i> {% translate "Cards & Discipline Ranking" %}
        </h5>
        <span class="badge bg-slate-800 text-slate-400 small px-2.5 py-1" style="font-weight: 700;">{% translate "Avg per Match" %}</span>
    </div>
    
    <div class="bg-black bg-opacity-25 border-bottom border-white border-opacity-5 px-3 py-2 d-none d-sm-flex justify-content-between align-items-center text-slate-400" style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
        <div>{% translate "Team" %}</div>
        <div class="d-flex gap-2">
            <div style="width: 85px; text-align: center;" title="{% translate 'Average yellow cards' %}">
                <i class="fa-solid fa-square text-warning me-1"></i> {% translate "Yellow" %}
            </div>
            <div style="width: 85px; text-align: center;" title="{% translate 'Average red cards' %}">
                <i class="fa-solid fa-square text-danger me-1"></i> {% translate "Red" %}
            </div>
        </div>
    </div>

    <div class="card-body p-1 overflow-auto custom-scrollbar" style="max-height: 375px;">
        <div class="d-flex flex-column gap-1">
            {% for s in team_stats|dictsortreversed:"avg_yellow" %}
            <div class="team-stat-card d-flex flex-column flex-sm-row justify-content-between align-items-sm-center px-3 py-2">
                <div class="d-flex align-items-center gap-3">
                    {% if s.team.logo_url %}
                    <img src="{{ s.team.logo_url }}" alt="{{ s.team.name }}" style="width: 28px; height: 28px; object-fit: contain;">
                    {% else %}
                    <div class="team-initial-box-sm">
                        {{ s.team.name|slice:":1" }}
                    </div>
                    {% endif %}
                    <div>
                        <a href="{% url 'matches:team_detail' s.team.id %}" class="text-decoration-none text-white fw-bold hover-primary" style="font-size: 0.88rem;">
                            {{ s.team.name }}
                        </a>
                        <span class="text-slate-500 d-block" style="font-size: 0.68rem;">{{ s.gp }} {% translate "matches" %}</span>
                    </div>
                </div>
                <div class="d-flex gap-2 flex-wrap mt-2 mt-sm-0">
                    <div class="stat-pill-badge-sm against-badge" style="width: 85px; justify-content: space-between; border-color: rgba(234, 179, 8, 0.2);" title="{% translate 'Average yellow cards' %}">
                        <span class="label"><i class="fa-solid fa-square text-warning me-1"></i></span>
                        <span class="value" style="background: rgba(234, 179, 8, 0.15); color: #facc15 !important;">{{ s.avg_yellow }}</span>
                    </div>
                    <div class="stat-pill-badge-sm against-badge" style="width: 85px; justify-content: space-between; border-color: rgba(239, 68, 68, 0.2);" title="{% translate 'Average red cards' %}">
                        <span class="label"><i class="fa-solid fa-square text-danger me-1"></i></span>
                        <span class="value" style="background: rgba(239, 68, 68, 0.15); color: #f87171 !important;">{{ s.avg_red }}</span>
                    </div>
                </div>
            </div>
            {% empty %}
            <div class="text-center py-5 text-slate-400">
                <i class="fa-solid fa-circle-exclamation fs-3 mb-2 d-block text-warning"></i>
                {% translate "No card data available yet." %}
            </div>
            {% endfor %}
        </div>
    </div>
</div>
'''

shots_card_html = '''
<!-- Shots Ranking -->
<div class="custom-card d-flex flex-column h-100">
    <div class="card-header bg-transparent border-bottom border-white border-opacity-5 p-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
        <h5 class="mb-0 text-white fw-bold d-flex align-items-center gap-2" style="font-size: 1.1rem;">
            <i class="fa-solid fa-crosshairs text-success"></i> {% translate "Shots per Match" %}
        </h5>
        <span class="badge bg-slate-800 text-slate-400 small px-2.5 py-1" style="font-weight: 700;">{% translate "Avg per Match" %}</span>
    </div>
    
    <div class="bg-black bg-opacity-25 border-bottom border-white border-opacity-5 px-3 py-2 d-none d-sm-flex justify-content-between align-items-center text-slate-400" style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
        <div>{% translate "Team" %}</div>
        <div class="d-flex gap-2">
            <div style="width: 85px; text-align: center;" title="{% translate 'Average shots per match' %}">
                <i class="fa-solid fa-bullseye text-success me-1"></i> {% translate "Shots" %}
            </div>
        </div>
    </div>

    <div class="card-body p-1 overflow-auto custom-scrollbar" style="max-height: 375px;">
        <div class="d-flex flex-column gap-1">
            {% for s in team_stats|dictsortreversed:"avg_shots" %}
            <div class="team-stat-card d-flex flex-column flex-sm-row justify-content-between align-items-sm-center px-3 py-2">
                <div class="d-flex align-items-center gap-3">
                    {% if s.team.logo_url %}
                    <img src="{{ s.team.logo_url }}" alt="{{ s.team.name }}" style="width: 28px; height: 28px; object-fit: contain;">
                    {% else %}
                    <div class="team-initial-box-sm">
                        {{ s.team.name|slice:":1" }}
                    </div>
                    {% endif %}
                    <div>
                        <a href="{% url 'matches:team_detail' s.team.id %}" class="text-decoration-none text-white fw-bold hover-primary" style="font-size: 0.88rem;">
                            {{ s.team.name }}
                        </a>
                        <span class="text-slate-500 d-block" style="font-size: 0.68rem;">{{ s.gp }} {% translate "matches" %}</span>
                    </div>
                </div>
                <div class="d-flex gap-2 flex-wrap mt-2 mt-sm-0">
                    <div class="stat-pill-badge-sm for-badge" style="width: 85px; justify-content: space-between;" title="{% translate 'Average shots' %}">
                        <span class="label"><i class="fa-solid fa-crosshairs text-success me-1"></i></span>
                        <span class="value">{{ s.avg_shots }}</span>
                    </div>
                </div>
            </div>
            {% empty %}
            <div class="text-center py-5 text-slate-400">
                <i class="fa-solid fa-circle-exclamation fs-3 mb-2 d-block text-warning"></i>
                {% translate "No shots data available yet." %}
            </div>
            {% endfor %}
        </div>
    </div>
</div>
'''

new_grid = f'''
    {{% cache 3600 league_detailed_stats league.id season.id %}}
    <div class="row g-4 mb-5">
        <!-- Corners -->
        <div class="col-xl-6">
            {corners_card_html}
        </div>
        
        <!-- Cards -->
        <div class="col-xl-6">
            {cards_card_html}
        </div>

        <!-- Shots -->
        <div class="col-xl-6">
            {shots_card_html}
        </div>

        <!-- Goal Timing -->
        <div class="col-xl-6">
            {goal_timing_html}
        </div>

        <!-- Top Scorers -->
        <div class="col-12">
            {top_scorers_html}
        </div>
    </div>
    {{% endcache %}}
    '''

new_content = content[:start_idx] + new_grid + '\n    ' + content[end_idx:]

with open('matches/templates/matches/league_detailed_stats.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
