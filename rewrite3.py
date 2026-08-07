import re

with open('matches/templates/matches/league_detailed_stats.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_str = '{% cache 3600 league_detailed_stats league.id season.id %}'
end_str = '{% endcache %}'

idx_start = content.find(start_str)
idx_end = content.find(end_str) + len(end_str)

if idx_start != -1 and idx_end != -1:
    original_block = content[idx_start:idx_end]
    
    new_block = '<div class="row g-4">\n    <!-- Main Content -->\n    <div class="col-lg-9" id="stats-content">\n        ' + original_block.replace('\n', '\n        ') + '\n    </div>\n    \n    <!-- Sidebar Placeholder -->\n    <div class="col-lg-3 d-none d-lg-block">\n        <div style="height: 600px; border: 1px dashed rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; color: rgba(255,255,255,0.3); border-radius: 8px;">\n            Anúncios / Sidebar\n        </div>\n    </div>\n</div>'
    
    new_content = content[:idx_start] + new_block + content[idx_end:]
    
    with open('matches/templates/matches/league_detailed_stats.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Wrapped cache block in col-lg-9')
else:
    print('Could not find cache block')
