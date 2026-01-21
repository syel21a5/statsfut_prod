
import os

file_path = r'c:\Users\VGR\.gemini\antigravity\scratch\betstats_python\matches\templates\matches\team_detail.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The exact problematic block pattern
# Note: whitespace might vary, so we'll try to match significant parts or use regex if needed.
# But let's try strict string replacement first of the lines we SAW in the view_file output.

target_block = """                    matches involving the team that had a total of over 2.5 goals, which is <span>{% if
                        goal_stats.match_total.total|get_key_pct:2.5 < league_over25_pct %}lower{% else %}higher{% endif
                            %}</span> than the league average value of <span>{{ league_over25_pct }}</span>% of league"""

replacement_block = """                    matches involving the team that had a total of over 2.5 goals, which is <span>{% if goal_stats.match_total.total|get_key_pct:2.5 < league_over25_pct %}lower{% else %}higher{% endif %}</span> than the league average value of <span>{{ league_over25_pct }}</span>% of league"""

if target_block in content:
    new_content = content.replace(target_block, replacement_block)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully replaced the split tag block.")
else:
    print("Could not find exact block match. Trying lines-based approach.")
    
    # Fallback: Find lines containing the split parts and join them
    lines = content.split('\n')
    new_lines = []
    skip_next = 0
    
    for i in range(len(lines)):
        if skip_next > 0:
            skip_next -= 1
            continue
            
        line = lines[i]
        # Check for the start of the split tag
        if "matches involving the team that had a total of over 2.5 goals, which is <span>{% if" in line:
            # We assume it spans 3 lines based on view_file output (1179, 1180, 1181)
            # 1179: ... <span>{% if
            # 1180: ... condition ...
            # 1181: ... %}</span> ...
            
            # Construct new line
            # We need to be careful about what part of line 1179 we keep vs replace
            # Validating if i+1 and i+2 exist
            
            # Let's clean the parts
            # Current line (i) ends with "<span>{% if"
            # Next line (i+1) starts with "goal_stats..." and ends with "{% endif"
            # Next line (i+2) starts with "%}</span>..."
            
            # Simply replacing the lines i, i+1, i+2 with the known good single line
            new_lines.append(replacement_block)
            skip_next = 2 # skip i+1 and i+2
        else:
            new_lines.append(line)
            
    final_content = '\n'.join(new_lines)
    if final_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print("Replaced content using line detection.")
    else:
        print("Failed to replace content. Structure might be different than expected.")

