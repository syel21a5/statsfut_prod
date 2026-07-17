import os
import re

os.system("git checkout matches/templates/matches/h2h_detail.html")

html_file = r'i:\GitHub\statsfut\statsfut\matches\templates\matches\h2h_detail.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. We need to find where `<div class="col-lg-9">` starts.
idx_start = content.find('<div class="col-lg-9">') + len('<div class="col-lg-9">\n')

# 2. We need to find where `<!-- Right Sidebar` starts to know the end of col-lg-9.
idx_end = content.find('<!-- Right Sidebar (25% Width) for Ads -->')
# We must find the closing </div> of col-lg-9 just before it.
idx_end = content.rfind('</div>', 0, idx_end)

main_content = content[idx_start:idx_end]

# 3. Now let's extract sections from main_content safely.
def extract_section(text, start_marker, end_marker=None):
    s = text.find(start_marker)
    if s == -1: return "", text
    if end_marker:
        e = text.find(end_marker, s)
        if e == -1: return "", text
    else:
        # If no end marker, just assume it's to the end or we don't extract
        return "", text
    block = text[s:e]
    new_text = text[:s] + text[e:]
    return block, new_text

# We need to parse out the blocks carefully.
# In the original file, it's just a sequence of cards/rows.
# Let's define the blocks we want for Aba 1, Aba 2, Aba 3.

# Aba 1 should have: Matchup Header Card, SEO Text, Recent H2H Matches, H2H History
# Aba 2 should have: Seasonal stats, form, comparison stats, etc.
# Aba 3 should have: Key Probabilities, Detailed Goal Stats, Estimated Probabilities, Points Per Game

# Wait, it's easier to just split by known markers and assemble.
markers = [
    ("<!-- Matchup Header Card -->", "<!-- H2H SEO Dynamic Text -->"),
    ("<!-- H2H SEO Dynamic Text -->", "<!-- MAIN GRID: Team 1 Column vs Team 2 Column -->"),
    ("<!-- MAIN GRID: Team 1 Column vs Team 2 Column -->", "<!-- Key Probabilities -->"),
    ("<!-- Key Probabilities -->", "<!-- Middle Ad Block -->"),
    ("<!-- Middle Ad Block -->", "<div class=\"row g-4\">\n                <!-- Comparison Stats (Total) -->"),
    ("<div class=\"row g-4\">\n                <!-- Comparison Stats (Total) -->", "<!-- NEW: Detailed Goals Analysis Grid -->"),
    ("<!-- NEW: Detailed Goals Analysis Grid -->", "<!-- Recent H2H Matches -->"),
    ("<!-- Recent H2H Matches -->", "<!-- Points Per Game"),
    ("<!-- Points Per Game", "{% if fallback_h2h %}"),
    ("{% if fallback_h2h %}", "<!-- Fallback End -->") # We'll just slice to the end for the last part
]

# Let's do it manually with regex or split to avoid missing divs.
# Actually, if I just inject the Tabs HTML at the top of col-lg-9, and inject <div class="tab-content">, 
# then inject `<div class="tab-pane active" id="frente">` before Matchup Header Card,
# then close it and open `<div class="tab-pane" id="comparacao">` before MAIN GRID,
# then close it and open `<div class="tab-pane" id="avancadas">` before Key Probabilities...
# WAIT, the blocks are interleaved!
# Key Probabilities is before Comparison Stats.
# Recent H2H Matches is AFTER Comparison Stats!
# This means I CANNOT just insert tab pane dividers. I MUST move blocks around.

# Let's extract blocks by regex.
# 1. Matchup Header Card & SEO
m_header = re.search(r'(<!-- Matchup Header Card -->.*?)(?=<!-- MAIN GRID)', main_content, re.DOTALL)
b_header = m_header.group(1) if m_header else ""

# 2. Main Grid (Seasonal Stats)
m_grid = re.search(r'(<!-- MAIN GRID.*?)(?=<!-- Key Probabilities -->)', main_content, re.DOTALL)
b_grid = m_grid.group(1) if m_grid else ""

# 3. Key Probabilities
m_kp = re.search(r'(<!-- Key Probabilities -->.*?)(?=<!-- Middle Ad Block -->)', main_content, re.DOTALL)
b_kp = m_kp.group(1) if m_kp else ""

# 4. Middle Ad Block
m_ad = re.search(r'(<!-- Middle Ad Block -->.*?</script>\n)', main_content, re.DOTALL) # wait, where is it?
m_ad = re.search(r'(<!-- Middle Ad Block -->.*?)(?=<div class="row g-4">\n                <!-- Comparison Stats)', main_content, re.DOTALL)
b_ad = m_ad.group(1) if m_ad else ""

# 5. Comparison Stats
m_comp = re.search(r'(<div class="row g-4">\n                <!-- Comparison Stats.*?)(?=<!-- NEW: Detailed Goals Analysis Grid -->)', main_content, re.DOTALL)
b_comp = m_comp.group(1) if m_comp else ""

# 6. Detailed Goals
m_goals = re.search(r'(<!-- NEW: Detailed Goals Analysis Grid -->.*?)(?=<!-- Recent H2H Matches -->)', main_content, re.DOTALL)
b_goals = m_goals.group(1) if m_goals else ""

# 7. Recent H2H Matches & Direct Head-to-Head History
m_recent = re.search(r'(<!-- Recent H2H Matches -->.*?)(?=<!-- Points Per Game)', main_content, re.DOTALL)
b_recent = m_recent.group(1) if m_recent else ""

# 8. Points Per Game
m_ppg = re.search(r'(<!-- Points Per Game.*?)(?={% if fallback_h2h %})', main_content, re.DOTALL)
b_ppg = m_ppg.group(1) if m_ppg else ""

# 9. Fallback
m_fall = re.search(r'({% if fallback_h2h %}.*?{% endif %}\n)', main_content, re.DOTALL)
b_fall = m_fall.group(1) if m_fall else ""

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

# Assembly
aba1 = f'<div class="tab-pane fade show active" id="frente" role="tabpanel">\n{b_header}\n{b_recent}\n</div>'
aba2 = f'<div class="tab-pane fade" id="comparacao" role="tabpanel">\n{b_grid}\n{b_comp}\n{b_ppg}\n</div>'
aba3 = f'<div class="tab-pane fade" id="avancadas" role="tabpanel">\n{cta_html}\n{b_kp}\n{b_goals}\n{b_fall}\n</div>'

new_main_content = f'{tabs_nav}\n<div class="tab-content" id="h2hTabsContent">\n{aba1}\n{aba2}\n{aba3}\n</div>'

# Now we also need to add scrollbars to Results boxes in aba2.
# We'll just replace the string in new_main_content
results_target = '<div class="table-responsive">\n                                <table class="table table-dark table-hover mb-0 align-middle small">\n                                    <thead>'
results_replace = '<div class="table-responsive custom-scrollbar" style="max-height: 350px; overflow-y: auto;">\n                                <table class="table table-dark table-hover mb-0 align-middle small">\n                                    <thead class="sticky-top" style="background-color: #1a1e29; z-index: 2;">'
new_main_content = new_main_content.replace(results_target, results_replace)


final_html = content[:idx_start] + new_main_content + '\n' + content[idx_end:]

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(final_html)

print("Rebuild Complete")
