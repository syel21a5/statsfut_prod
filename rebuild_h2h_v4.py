import os
import re

os.system("git checkout matches/templates/matches/h2h_detail.html")

html_file = r'i:\GitHub\statsfut\statsfut\matches\templates\matches\h2h_detail.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to wrap the contents of col-lg-9 inside the Tabs structure.
# Let's find exactly where we want to insert things.

# 1. Insert Tabs Nav right after `<div class="col-lg-9">`
idx_col9 = content.find('<div class="col-lg-9">') + len('<div class="col-lg-9">\n')

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

# 2. Start Aba 1 before `<!-- Matchup Header Card -->`
idx_aba1_start = content.find('            <!-- Matchup Header Card -->')
if idx_aba1_start != -1:
    content = content[:idx_aba1_start] + '                <div class="tab-pane fade show active" id="frente" role="tabpanel">\n' + content[idx_aba1_start:]

# 3. We want `Recent H2H Matches` to be in Aba 1. But it's further down.
# Let's extract `Recent H2H Matches` completely.
# It starts at `                <!-- Recent H2H Matches -->` and ends after its closing `</div>`
# Wait, it's inside `row g-4`.
# We'll just extract the `col-lg-4` that contains `Recent H2H Matches`.
idx_recent_start = content.find('                <!-- Recent H2H Matches -->')
idx_recent_end = content.find('                </div>\n            </div>\n\n            <!-- NEW: Detailed Goals Analysis Grid -->')
if idx_recent_start != -1 and idx_recent_end != -1:
    # Add the closing </div> of col-lg-4
    idx_recent_end += len('                </div>\n')
    recent_block = content[idx_recent_start:idx_recent_end]
    content = content[:idx_recent_start] + content[idx_recent_end:]
    
    # We also need to close the `row g-4` that was containing it, because we just removed the last column.
    # Wait, in the original file, the `</div>` that closes `row g-4` was at `            </div>\n\n            <!-- NEW: Detailed Goals Analysis Grid -->`.
    # So the `row g-4` is STILL properly closed! Because we didn't remove `            </div>\n`
    
    # Let's insert `recent_block` at the end of Aba 1!
    # Where does Aba 1 end? Before `<!-- MAIN GRID: Team 1 Column vs Team 2 Column -->`
    idx_aba1_end = content.find('            <!-- MAIN GRID: Team 1 Column vs Team 2 Column -->')
    # Wrap recent_block in a row
    recent_block = '                <div class="row g-4 mb-4">\n' + recent_block + '                </div>\n'
    content = content[:idx_aba1_end] + recent_block + '                </div><!-- End Aba 1 -->\n' + content[idx_aba1_end:]

# 4. Start Aba 2 before `<!-- MAIN GRID -->`
idx_aba2_start = content.find('            <!-- MAIN GRID: Team 1 Column vs Team 2 Column -->')
content = content[:idx_aba2_start] + '                <div class="tab-pane fade" id="comparacao" role="tabpanel">\n' + content[idx_aba2_start:]

# 5. Where does Aba 2 end? Before `<!-- Key Probabilities -->`
idx_aba2_end = content.find('            <!-- Key Probabilities -->')
content = content[:idx_aba2_end] + '                </div><!-- End Aba 2 -->\n' + content[idx_aba2_end:]

# 6. Start Aba 3 before `<!-- Key Probabilities -->`
idx_aba3_start = content.find('            <!-- Key Probabilities -->')

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
content = content[:idx_aba3_start] + '                <div class="tab-pane fade" id="avancadas" role="tabpanel">\n' + cta_html + content[idx_aba3_start:]

# 7. Where does Aba 3 end? At the end of `col-lg-9`.
# The `col-lg-9` ends at `        </div>\n        <!-- Right Sidebar (25% Width) for Ads -->`
# Wait, it actually ends at `            {% endif %}\n        </div>`
idx_aba3_end = content.find('        <!-- Right Sidebar (25% Width) for Ads -->')
idx_aba3_end = content.rfind('        </div>', 0, idx_aba3_end)
content = content[:idx_aba3_end] + '                </div><!-- End Aba 3 -->\n            </div><!-- End Tabs Content -->\n' + content[idx_aba3_end:]

# 8. Add tabs_nav at the top of col-lg-9
idx_col9 = content.find('<div class="col-lg-9">') + len('<div class="col-lg-9">\n')
content = content[:idx_col9] + tabs_nav + content[idx_col9:]

# 9. Add scrollbar to results tables.
results_target = '<div class="table-responsive">\n                                <table class="table table-dark table-hover mb-0 align-middle small">\n                                    <thead>'
results_replace = '<div class="table-responsive custom-scrollbar" style="max-height: 350px; overflow-y: auto;">\n                                <table class="table table-dark table-hover mb-0 align-middle small">\n                                    <thead class="sticky-top" style="background-color: #1a1e29; z-index: 2;">'
content = content.replace(results_target, results_replace)

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Script 4 Executed.")
