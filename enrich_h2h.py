import re

html_file = r'i:\GitHub\statsfut\statsfut\matches\templates\matches\h2h_detail.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. We need to find the `Recent H2H Matches` block.
# Wait, let's just locate the Aba 1 content.
aba1_start = content.find('<div class="tab-pane fade show active" id="frente" role="tabpanel">')
aba1_end = content.find('                </div><!-- End Aba 1 -->')

aba1_content = content[aba1_start:aba1_end]

# In Aba1, we currently have:
# <div class="row g-4">
#   <div class="col-lg-4"> <!-- Comparison Stats --> </div>
#   <div class="col-lg-4"> <!-- Home vs Away --> </div>
#   <div class="col-lg-4"> <!-- Recent H2H Matches --> </div>
# </div>

# We will modify it.
# First, change the first two `col-lg-4` to `col-lg-6`.
# We know the first one starts right after `<!-- Comparison Stats (Total) -->`
c_start = aba1_content.find('<!-- Comparison Stats (Total) -->')
# We need to find the `<div class="col-lg-4">` right ABOVE it.
col1_idx = aba1_content.rfind('<div class="col-lg-4">', 0, c_start)
aba1_content = aba1_content[:col1_idx] + '<div class="col-lg-6">' + aba1_content[col1_idx+22:]

c_home_start = aba1_content.find('<!-- Home vs Away Specifics -->')
col2_idx = aba1_content.rfind('<div class="col-lg-4">', 0, c_home_start)
aba1_content = aba1_content[:col2_idx] + '<div class="col-lg-6">' + aba1_content[col2_idx+22:]

# Now, extract the third column entirely.
c_recent_start = aba1_content.find('<!-- Recent H2H Matches -->')
col3_idx = aba1_content.rfind('<div class="col-lg-4">', 0, c_recent_start)

# Find the end of col3.
# It ends with `</div>\n            </div>\n` (closing col3, then closing row).
# We can find the closing `</div>` of col3.
# The card ends, then col3 ends.
# We'll just split exactly there.
end_col3 = aba1_content.find('                </div>\n            </div>', col3_idx)
col3_content = aba1_content[col3_idx:end_col3]

# Remove col3 from the row
aba1_content = aba1_content[:col3_idx] + aba1_content[end_col3:]

# Now we rewrite the Recent H2H block to be full width and rich.
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

# Append the rich recent block to the end of aba1_content
aba1_content = aba1_content + rich_recent

# Replace in original content
content = content[:aba1_start] + aba1_content + content[aba1_end:]

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Enrich Aba 1 executed.")
