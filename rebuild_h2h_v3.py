import os

os.system("git checkout matches/templates/matches/h2h_detail.html")

html_file = r'i:\GitHub\statsfut\statsfut\matches\templates\matches\h2h_detail.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Substrings to split the content perfectly.
# Everything is sequentially laid out.
# col-lg-9 content begins at <!-- Matchup Header Card -->
idx_start = content.find('            <!-- Matchup Header Card -->')

# Fallback H2H ends at {% endif %} right before </div> <!-- Right Sidebar -->
idx_end = content.find('            {% endif %}\n        </div>') + len('            {% endif %}\n')

main_content = content[idx_start:idx_end]

s1 = '            <!-- Matchup Header Card -->'
s2 = '            <!-- MAIN GRID: Team 1 Column vs Team 2 Column -->'
s3 = '            <!-- Key Probabilities -->'
s4 = '    <!-- Middle Ad Block -->'
s5 = '<div class="row g-4">\n                <!-- Comparison Stats (Total) -->'
s6 = '                <!-- Recent H2H Matches -->'
s7 = '            <!-- NEW: Detailed Goals Analysis Grid -->'
s8 = '            <!-- Points Per Game (Remaining Matches Analysis) -->'
s9 = '            {% if fallback_h2h %}'

# We will cut main_content using these exact strings.
def get_chunk(c, start, end):
    if end:
        return c[c.find(start):c.find(end)]
    else:
        return c[c.find(start):]

chunk_header = get_chunk(main_content, s1, s2)
chunk_maingrid = get_chunk(main_content, s2, s3)
chunk_kp = get_chunk(main_content, s3, s4)
chunk_ad = get_chunk(main_content, s4, s5)

# For s5 to s7, it's a `<div class="row g-4">`.
# It contains: Comparison Stats, Home vs Away, Recent H2H Matches.
# Wait, s6 is INSIDE s5's row!
# So chunk_comp (s5 to s6) is the row start + Comparison + Home vs Away
chunk_comp = get_chunk(main_content, s5, s6)
# chunk_recent (s6 to s7) is Recent H2H + the closing </div> of the row g-4!
chunk_recent = get_chunk(main_content, s6, s7)

chunk_goals_and_avg = get_chunk(main_content, s7, s8)
chunk_ppg = get_chunk(main_content, s8, s9)
chunk_fallback = get_chunk(main_content, s9, None)

# Now, we want:
# Aba 1: chunk_header, chunk_recent (wait, chunk_recent has the closing </div> for the row from s5! If we move it, the div will be unbalanced!)
# Ah! We must NOT move chunk_recent blindly!
# chunk_recent is: 
#                 <!-- Recent H2H Matches -->
#                 <div class="col-lg-4"> ... </div>
#             </div>
# We need to strip the trailing `</div>` from chunk_recent, and append a `</div>` to chunk_comp!
# Let's fix chunk_comp:
chunk_comp += '            </div>\n'
# Let's fix chunk_recent:
# Find the last </div> in chunk_recent and remove it.
last_div = chunk_recent.rfind('</div>')
if last_div != -1:
    chunk_recent = chunk_recent[:last_div]

# Wait, `chunk_recent` might also need a `<div class="row g-4">` wrapped around it if we move it to Aba 1!
chunk_recent = '<div class="row g-4">\n' + chunk_recent + '</div>\n'

# Aba 2: chunk_maingrid, chunk_comp, chunk_ppg
# Aba 3: cta, chunk_kp, chunk_goals_and_avg, chunk_fallback

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
"""

aba1 = f'<div class="tab-pane fade show active" id="frente" role="tabpanel">\n{chunk_header}{chunk_recent}</div>\n'
aba2 = f'<div class="tab-pane fade" id="comparacao" role="tabpanel">\n{chunk_maingrid}{chunk_comp}{chunk_ppg}</div>\n'
aba3 = f'<div class="tab-pane fade" id="avancadas" role="tabpanel">\n{cta_html}{chunk_kp}{chunk_goals_and_avg}{chunk_fallback}</div>\n'

new_main_content = f'{tabs_nav}<div class="tab-content" id="h2hTabsContent">\n{aba1}{aba2}{aba3}</div>\n'

results_target = '<div class="table-responsive">\n                                <table class="table table-dark table-hover mb-0 align-middle small">\n                                    <thead>'
results_replace = '<div class="table-responsive custom-scrollbar" style="max-height: 350px; overflow-y: auto;">\n                                <table class="table table-dark table-hover mb-0 align-middle small">\n                                    <thead class="sticky-top" style="background-color: #1a1e29; z-index: 2;">'
new_main_content = new_main_content.replace(results_target, results_replace)

final_html = content[:idx_start] + new_main_content + content[idx_end:]

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(final_html)

print("Rebuild Complete")
