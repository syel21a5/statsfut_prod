import re

with open('matches/templates/matches/league_detailed_stats.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = '{% cache 3600 league_detailed_stats league.id season.id %}'
end_marker = '{% endcache %}'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker) + len(end_marker)

new_grid = '''{% cache 3600 league_detailed_stats league.id season.id %}
    <div class="row g-4 mb-5">
        <!-- Corners -->
        <div class="col-lg-6">
            <div class="card border-0 bg-white bg-opacity-10 text-white shadow-sm h-100">
                <div class="card-header bg-transparent border-bottom border-secondary border-opacity-25 py-2">
                    <h6 class="mb-0 fw-bold small text-uppercase"><i class="fa-solid fa-flag me-2 text-info"></i>{% translate "Corners Performance Ranking" %}</h6>
                </div>
                <div class="card-body p-0 overflow-auto custom-scrollbar" style="max-height: 400px;">
                    <div class="table-responsive">
                        <table class="table table-dark table-sm mb-0 text-center small align-middle">
                            <thead style="position: sticky; top: 0; background: #1a1e29; z-index: 1;">
                                <tr class="text-secondary">
                                    <th class="text-start ps-3">{% translate "Team" %}</th>
                                    <th><i class="fa-solid fa-arrow-up-long text-success me-1"></i>{% translate "For" %}</th>
                                    <th><i class="fa-solid fa-arrow-down-long text-danger me-1"></i>{% translate "Against" %}</th>
                                    <th class="text-info pe-3">{% translate "Total" %}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for s in team_stats %}
                                <tr>
                                    <td class="text-start ps-3 fw-bold">
                                        {% if s.team.logo_url %}
                                        <img src="{{ s.team.logo_url }}" alt="{{ s.team.name }}" class="me-2" style="width: 20px; height: 20px; object-fit: contain;">
                                        {% endif %}
                                        <a href="{% url 'matches:team_detail' s.team.id %}" class="text-decoration-none text-white hover-primary">
                                            {{ s.team.name }}
                                        </a>
                                    </td>
                                    <td>{{ s.avg_corners_for }}</td>
                                    <td>{{ s.avg_corners_against }}</td>
                                    <td class="fw-bold text-info pe-3">{{ s.avg_corners_total }}</td>
                                </tr>
                                {% empty %}
                                <tr>
                                    <td colspan="4" class="text-center py-4 text-slate-400">
                                        <i class="fa-solid fa-circle-exclamation mb-2 d-block"></i>
                                        {% translate "No data available." %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Cards -->
        <div class="col-lg-6">
            <div class="card border-0 bg-white bg-opacity-10 text-white shadow-sm h-100">
                <div class="card-header bg-transparent border-bottom border-secondary border-opacity-25 py-2">
                    <h6 class="mb-0 fw-bold small text-uppercase"><i class="fa-solid fa-copy me-2 text-warning"></i>{% translate "Cards & Discipline Ranking" %}</h6>
                </div>
                <div class="card-body p-0 overflow-auto custom-scrollbar" style="max-height: 400px;">
                    <div class="table-responsive">
                        <table class="table table-dark table-sm mb-0 text-center small align-middle">
                            <thead style="position: sticky; top: 0; background: #1a1e29; z-index: 1;">
                                <tr class="text-secondary">
                                    <th class="text-start ps-3">{% translate "Team" %}</th>
                                    <th><i class="fa-solid fa-square text-warning me-1"></i>{% translate "Yellow" %}</th>
                                    <th class="pe-3"><i class="fa-solid fa-square text-danger me-1"></i>{% translate "Red" %}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for s in team_stats|dictsortreversed:"avg_yellow" %}
                                <tr>
                                    <td class="text-start ps-3 fw-bold">
                                        {% if s.team.logo_url %}
                                        <img src="{{ s.team.logo_url }}" alt="{{ s.team.name }}" class="me-2" style="width: 20px; height: 20px; object-fit: contain;">
                                        {% endif %}
                                        <a href="{% url 'matches:team_detail' s.team.id %}" class="text-decoration-none text-white hover-primary">
                                            {{ s.team.name }}
                                        </a>
                                    </td>
                                    <td class="fw-bold text-warning">{{ s.avg_yellow }}</td>
                                    <td class="fw-bold text-danger pe-3">{{ s.avg_red }}</td>
                                </tr>
                                {% empty %}
                                <tr>
                                    <td colspan="3" class="text-center py-4 text-slate-400">
                                        <i class="fa-solid fa-circle-exclamation mb-2 d-block"></i>
                                        {% translate "No data available." %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Shots -->
        <div class="col-lg-6">
            <div class="card border-0 bg-white bg-opacity-10 text-white shadow-sm h-100">
                <div class="card-header bg-transparent border-bottom border-secondary border-opacity-25 py-2">
                    <h6 class="mb-0 fw-bold small text-uppercase"><i class="fa-solid fa-crosshairs me-2 text-success"></i>{% translate "Shots per Match" %}</h6>
                </div>
                <div class="card-body p-0 overflow-auto custom-scrollbar" style="max-height: 400px;">
                    <div class="table-responsive">
                        <table class="table table-dark table-sm mb-0 text-center small align-middle">
                            <thead style="position: sticky; top: 0; background: #1a1e29; z-index: 1;">
                                <tr class="text-secondary">
                                    <th class="text-start ps-3">{% translate "Team" %}</th>
                                    <th class="text-success pe-3"><i class="fa-solid fa-bullseye me-1"></i>{% translate "Shots (Avg)" %}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for s in team_stats|dictsortreversed:"avg_shots" %}
                                <tr>
                                    <td class="text-start ps-3 fw-bold">
                                        {% if s.team.logo_url %}
                                        <img src="{{ s.team.logo_url }}" alt="{{ s.team.name }}" class="me-2" style="width: 20px; height: 20px; object-fit: contain;">
                                        {% endif %}
                                        <a href="{% url 'matches:team_detail' s.team.id %}" class="text-decoration-none text-white hover-primary">
                                            {{ s.team.name }}
                                        </a>
                                    </td>
                                    <td class="fw-bold text-success pe-3">{{ s.avg_shots }}</td>
                                </tr>
                                {% empty %}
                                <tr>
                                    <td colspan="2" class="text-center py-4 text-slate-400">
                                        <i class="fa-solid fa-circle-exclamation mb-2 d-block"></i>
                                        {% translate "No data available." %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Goal Timing -->
        <div class="col-lg-6">
            <div class="card border-0 bg-white bg-opacity-10 text-white shadow-sm h-100">
                <div class="card-header bg-transparent border-bottom border-secondary border-opacity-25 py-2">
                    <h6 class="mb-0 fw-bold small text-uppercase"><i class="fa-solid fa-clock me-2 text-info"></i>{% translate "Goal Minutes Distribution" %}</h6>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-dark table-sm mb-0 text-center small align-middle">
                            <thead>
                                <tr class="text-secondary">
                                    <th class="text-start ps-3">{% translate "Period" %}</th>
                                    <th>{% translate "Goals" %}</th>
                                    <th class="text-end pe-3">%</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for t in timing_stats %}
                                <tr>
                                    <td class="text-start ps-3 text-secondary">{{ t.period }}</td>
                                    <td>{{ t.count }}</td>
                                    <td class="text-end pe-3">
                                        <div class="d-flex align-items-center justify-content-end gap-2">
                                            <span>{{ t.pct|floatformat:1 }}%</span>
                                            <div class="progress" style="width: 50px; height: 4px;">
                                                 <div class="progress-bar bg-info" role="progressbar" style="width: {{ t.pct }}%;"></div>
                                             </div>
                                        </div>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Top Scorers -->
        <div class="col-lg-6">
            <div class="card border-0 bg-white bg-opacity-10 text-white shadow-sm h-100">
                <div class="card-header bg-transparent border-bottom border-secondary border-opacity-25 py-2">
                    <h6 class="mb-0 fw-bold small text-uppercase"><i class="fa-solid fa-fire me-2 text-warning"></i>{% translate "League Top Scorers" %}</h6>
                </div>
                <div class="card-body p-0 overflow-auto custom-scrollbar" style="max-height: 400px;">
                    <div class="table-responsive">
                        <table class="table table-dark table-sm mb-0 text-center small align-middle">
                            <thead style="position: sticky; top: 0; background: #1a1e29; z-index: 1;">
                                <tr class="text-secondary">
                                    <th class="text-start ps-3">{% translate "Player" %}</th>
                                    <th>{% translate "Team" %}</th>
                                    <th class="text-end pe-3">{% translate "Goals" %}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for p in top_scorers %}
                                <tr>
                                    <td class="text-start ps-3 fw-bold">{{ p.player_name }}</td>
                                    <td class="text-secondary" style="font-size: 0.75rem;">{{ p.team__name }}</td>
                                    <td class="fw-bold text-warning text-end pe-3">
                                        {{ p.goals_count }}
                                        {% if p.penalties > 0 %}
                                        <span class="text-secondary" style="font-size: 0.65rem;">({{ p.penalties }} Pen)</span>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% empty %}
                                <tr>
                                    <td colspan="3" class="text-center py-4 text-slate-400">
                                        <i class="fa-solid fa-circle-exclamation mb-2 d-block"></i>
                                        {% translate "No data available." %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
{% endcache %}'''

new_content = content[:start_idx] + new_grid + content[end_idx:]

with open('matches/templates/matches/league_detailed_stats.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
