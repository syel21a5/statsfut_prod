with open('matches/templates/matches/league_goals.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
in_timing = False
for i, line in enumerate(lines):
    if 'premium-tabs mb-4 flex-wrap" id="timingSubTabs"' in line:
        lines[i] = line.replace('mb-4', 'mb-2')
    
    if 'id="timing"' in line:
        in_timing = True
        
    if in_timing:
        if 'card-body p-3' in line:
            lines[i] = line.replace('card-body p-3', 'card-body px-3 pb-3 pt-1')
        elif 'card-body p-4' in line:
            lines[i] = line.replace('card-body p-4', 'card-body px-4 pb-4 pt-1')
        if 'nav-sm mb-3' in line:
            lines[i] = line.replace('nav-sm mb-3', 'nav-sm mb-1')

with open('matches/templates/matches/league_goals.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)
