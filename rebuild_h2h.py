import os

html_file = r'i:\GitHub\statsfut\statsfut\matches\templates\matches\h2h_detail.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Rename Tabs
content = content.replace(
    '<button class="nav-link active" id="frente-tab" data-bs-toggle="tab" data-bs-target="#frente" type="button" role="tab" aria-controls="frente" aria-selected="true"><i class="fa-solid fa-handshake-angle me-2"></i>Frente a Frente</button>',
    '<button class="nav-link active" id="frente-tab" data-bs-toggle="tab" data-bs-target="#frente" type="button" role="tab" aria-controls="frente" aria-selected="true"><i class="fa-solid fa-handshake-angle me-2"></i>Histórico Direto</button>'
)
content = content.replace(
    '<button class="nav-link" id="comparacao-tab" data-bs-toggle="tab" data-bs-target="#comparacao" type="button" role="tab" aria-controls="comparacao" aria-selected="false"><i class="fa-solid fa-scale-balanced me-2"></i>Comparação (Temporada)</button>',
    '<button class="nav-link" id="comparacao-tab" data-bs-toggle="tab" data-bs-target="#comparacao" type="button" role="tab" aria-controls="comparacao" aria-selected="false"><i class="fa-solid fa-scale-balanced me-2"></i>Forma e Estatísticas</button>'
)
content = content.replace(
    '<button class="nav-link" id="avancadas-tab" data-bs-toggle="tab" data-bs-target="#avancadas" type="button" role="tab" aria-controls="avancadas" aria-selected="false"><i class="fa-solid fa-chart-line me-2"></i>Sequências & Avançadas</button>',
    '<button class="nav-link" id="avancadas-tab" data-bs-toggle="tab" data-bs-target="#avancadas" type="button" role="tab" aria-controls="avancadas" aria-selected="false"><i class="fa-solid fa-chart-line me-2"></i>Análise Avançada</button>'
)

# 2. Add Scrollbars to Results boxes
# There are two <div class="table-responsive"> right after <h6 class="mb-0 fw-bold small text-uppercase">{% translate "Results" %}</h6>
results_target = """<h6 class="mb-0 fw-bold small text-uppercase">{% translate "Results" %}</h6>
                        </div>
                        <div class="card-body p-0">
                            <div class="table-responsive">
                                <table class="table table-dark table-hover mb-0 align-middle small">
                                    <thead>"""
results_replace = """<h6 class="mb-0 fw-bold small text-uppercase">{% translate "Results" %}</h6>
                        </div>
                        <div class="card-body p-0">
                            <div class="table-responsive custom-scrollbar" style="max-height: 350px; overflow-y: auto;">
                                <table class="table table-dark table-hover mb-0 align-middle small">
                                    <thead class="sticky-top" style="background-color: #1a1e29; z-index: 2;">"""
content = content.replace(results_target, results_replace)


def extract_block(start_str, end_str):
    global content
    idx1 = content.find(start_str)
    if idx1 == -1: return ""
    idx2 = content.find(end_str, idx1)
    if idx2 == -1: return ""
    idx2 += len(end_str)
    block = content[idx1:idx2]
    content = content[:idx1] + content[idx2:]
    return block

# 3. Extract Blocks to Move
# Key Probabilities
idx_kp = content.find("<!-- Key Probabilities -->")
idx_rh = content.find("<!-- Recent H2H Matches -->")
if idx_kp != -1 and idx_rh != -1:
    b1 = content[idx_kp:idx_rh]
    content = content[:idx_kp] + content[idx_rh:]
else:
    b1 = ""

# Fallback H2H (Estimated Probabilities)
b2 = extract_block("{% if fallback_h2h %}\n            <div class=\"row mt-4\">", "            {% endif %}\n")

# Detailed Goals Analysis Grid and Comparison with league average
idx_dg = content.find("<!-- NEW: Detailed Goals Analysis Grid -->")
idx_a3 = content.find("<!-- Aba 3: Sequências & Avançadas -->")
if idx_dg != -1 and idx_a3 != -1:
    b3 = content[idx_dg:idx_a3]
    content = content[:idx_dg] + content[idx_a3:]
else:
    b3 = ""

# 4. Inject CTA and Blocks into Aba 3
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

aba3_marker = '<!-- Aba 3: Sequências & Avançadas -->\n                <div class="tab-pane fade" id="avancadas" role="tabpanel" aria-labelledby="avancadas-tab">\n'

# We append CTA, then b1 (Key Probs), then b3 (Detailed Goals & League Comp), then b2 (Fallback H2H)
aba3_content = cta_html + "\n" + b1 + "\n" + b3 + "\n" + b2

content = content.replace(aba3_marker, aba3_marker + aba3_content)


with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done reconstructing h2h_detail.html")
