import re

with open('matches/templates/matches/league_detailed_stats.html', 'r', encoding='utf-8') as f:
    content = f.read()

def inject_footer(html, marker, footer_text):
    # Find the table block and add footer after it
    # But wait, it's inside `card-body p-0 overflow-auto`. If we add it there, it will scroll.
    # We should add it inside `card-body` but outside `table-responsive`.
    # Wait, in the goals page:
    # <div class="card-body p-0">
    #     <div class="table-responsive">...</div>
    #     <div class="p-3 border-top border-secondary border-opacity-25 small text-secondary">...</div>
    # </div>
    # Let's search for the end of `table-responsive` inside each card.
    
    # We can split the content into cards and inject. But simpler:
    # Find the closing </div> of `table-responsive` for each card and insert.
    pass

# Corners
corners_footer = '''</div>
                    <div class="p-3 border-top border-secondary border-opacity-25 small text-secondary">
                        <span class="fst-italic"><i class="fa-solid fa-circle-info me-1"></i> {% translate "Ranking of teams with the most corners on average per match (For, Against and Total)." %}</span>
                    </div>'''
content = re.sub(r'(<!-- Corners -->.*?</table>\s*</div>\s*)</div>', r'\1' + corners_footer, content, flags=re.DOTALL)

# Cards
cards_footer = '''</div>
                    <div class="p-3 border-top border-secondary border-opacity-25 small text-secondary">
                        <span class="fst-italic"><i class="fa-solid fa-circle-info me-1"></i> {% translate "Disciplinary ranking showing the teams with the most yellow and red cards per match." %}</span>
                    </div>'''
content = re.sub(r'(<!-- Cards -->.*?</table>\s*</div>\s*)</div>', r'\1' + cards_footer, content, flags=re.DOTALL)

# Shots
shots_footer = '''</div>
                    <div class="p-3 border-top border-secondary border-opacity-25 small text-secondary">
                        <span class="fst-italic"><i class="fa-solid fa-circle-info me-1"></i> {% translate "Ranking of teams with the highest average number of shots per match." %}</span>
                    </div>'''
content = re.sub(r'(<!-- Shots -->.*?</table>\s*</div>\s*)</div>', r'\1' + shots_footer, content, flags=re.DOTALL)

# Goal Timing
timing_footer = '''</div>
                    <div class="p-3 border-top border-secondary border-opacity-25 small text-secondary">
                        <span class="fst-italic"><i class="fa-solid fa-circle-info me-1"></i> {% translate "Distribution of goals scored across 15-minute periods of the match." %}</span>
                    </div>'''
content = re.sub(r'(<!-- Goal Timing -->.*?</table>\s*</div>\s*)</div>', r'\1' + timing_footer, content, flags=re.DOTALL)

# Top Scorers
scorers_footer = '''</div>
                    <div class="p-3 border-top border-secondary border-opacity-25 small text-secondary">
                        <span class="fst-italic"><i class="fa-solid fa-circle-info me-1"></i> {% translate "League top scorers for the current season, including penalty goals." %}</span>
                    </div>'''
content = re.sub(r'(<!-- Top Scorers -->.*?</table>\s*</div>\s*)</div>', r'\1' + scorers_footer, content, flags=re.DOTALL)

with open('matches/templates/matches/league_detailed_stats.html', 'w', encoding='utf-8') as f:
    f.write(content)
