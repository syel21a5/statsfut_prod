import os

html_file = r'i:\GitHub\statsfut\statsfut\matches\templates\matches\h2h_detail.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the old CTA block from the top of Aba 3
old_cta_start = content.find('                    {% if next_match %}\n                    <div class="row mb-4">\n                        <div class="col-12">\n                            <div class="card border-0 bg-info bg-opacity-10')

if old_cta_start != -1:
    old_cta_end = content.find('                    {% endif %}\n            <!-- Key Probabilities -->', old_cta_start)
    if old_cta_end != -1:
        # Include `{% endif %}\n` in the removal
        old_cta_end += len('                    {% endif %}\n')
        
        # Remove it from content
        content = content[:old_cta_start] + content[old_cta_end:]

# 2. Inject the NEW Premium CTA block at the end of Aba 3.
# Aba 3 ends right before the tab-content closes.
# We will search for `                </div>\n            </div>\n        </div>\n        <!-- Right Sidebar (25% Width) for Ads -->`
# Wait, let's just find the closing tags of Aba 3.
aba3_end_idx = content.find('                </div>\n            </div>\n        </div>\n        <!-- Right Sidebar (25% Width) for Ads -->')

if aba3_end_idx == -1:
    # Let's try finding the last `</div>` of `avancadas` manually
    # Just insert it before `            </div>\n        </div>\n        <!-- Right Sidebar`
    aba3_end_idx = content.find('            </div>\n        </div>\n        <!-- Right Sidebar')

if aba3_end_idx != -1:
    premium_cta = """
                    <!-- PREMIUM CTA BANNER -->
                    {% if next_match %}
                    <div class="row mt-5 mb-2">
                        <div class="col-12">
                            <div class="card border-0 text-white position-relative overflow-hidden" style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5) !important;">
                                <!-- Glowing accent border -->
                                <div class="position-absolute top-0 start-0 w-100" style="height: 4px; background: linear-gradient(90deg, #0ea5e9, #8b5cf6, #ec4899);"></div>
                                
                                <!-- Background pattern/glow -->
                                <div class="position-absolute top-0 end-0 opacity-25" style="transform: translate(15%, -20%); pointer-events: none;">
                                    <i class="fa-solid fa-microchip" style="font-size: 15rem; color: #8b5cf6; filter: blur(4px);"></i>
                                </div>
                                
                                <div class="card-body p-4 p-md-5 position-relative z-index-1 d-flex flex-column flex-md-row align-items-center justify-content-between">
                                    <div class="text-start mb-4 mb-md-0 pe-md-4">
                                        <div class="d-flex align-items-center mb-2">
                                            <span class="badge bg-danger text-uppercase fw-bold tracking-wide me-2 px-2 py-1" style="font-size: 0.7rem; letter-spacing: 1px;"><i class="fa-solid fa-crown me-1"></i>PRO</span>
                                            <h3 class="fw-bold mb-0 text-white">Previsão Algorítmica da Partida</h3>
                                        </div>
                                        <p class="text-secondary mb-0 fs-6">
                                            O algoritmo da StatsFut já processou todos os dados de <strong class="text-light">{{ team1.name }}</strong> e <strong class="text-light">{{ team2.name }}</strong> para o próximo jogo. Desbloqueie a previsão matemática de <span class="text-info fw-bold">Over/Under</span>, <span class="text-warning fw-bold">Escanteios</span> e a <span class="text-success fw-bold">Dica da IA</span>.
                                        </p>
                                    </div>
                                    
                                    <div class="flex-shrink-0 text-center">
                                        <a href="{% url 'matches:match_detail' pk=next_match.pk slug=next_match.slug %}" class="btn fw-bold px-5 py-3 rounded-pill shadow-lg d-inline-flex align-items-center justify-content-center" style="background: linear-gradient(90deg, #0ea5e9, #3b82f6); color: white; transition: all 0.3s; border: none; font-size: 1.1rem;">
                                            <i class="fa-solid fa-unlock-keyhole me-2"></i>Acessar Previsão
                                        </a>
                                        <div class="small text-secondary mt-2 fw-bold tracking-wide"><i class="fa-solid fa-bolt text-warning me-1"></i>GERADO POR INTELIGÊNCIA ARTIFICIAL</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endif %}
"""
    content = content[:aba3_end_idx] + premium_cta + content[aba3_end_idx:]

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("CTA Upgraded successfully.")
