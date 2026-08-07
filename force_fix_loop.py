
import os

file_path = r'C:\Users\VGR\.gemini\antigravity\scratch\betstats_python\matches\templates\matches\team_detail.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Target block: lines 1182 to 1204 (in current file state)
# But wait, lines numbers might shift if previous edits changed length.
# We should find the block by content.
# Start: {% for match in run_in.matches|slice:":13" %}
# End: {% endfor %} (the one after the start)

start_idx = -1
for i, line in enumerate(lines):
    if '{% for match in run_in.matches|slice:":13" %}' in line:
        start_idx = i
        break

if start_idx == -1:
    print("ERROR: Could not find start of loop.")
    exit(1)

# Find matching endfor
end_idx = -1
for i in range(start_idx, len(lines)):
    if '{% endfor %}' in line: # Potentially risky if nested loops, but this snippet doesn't have nested loops
        # Actually line 1204 is just {% endfor %}
        if lines[i].strip() == '{% endfor %}':
            end_idx = i
            break

if end_idx == -1:
    # Try searching for the text literal if exact match fails
    for i in range(start_idx, len(lines)):
        if '{% endfor %}' in lines[i]:
             end_idx = i
             break

if end_idx == -1:
    print("ERROR: Could not find end of loop.")
    exit(1)

print(f"Replacing lines {start_idx+1} to {end_idx+1}")

new_block = [
    '                        {% for match in run_in.matches|slice:":13" %}\n',
    '                        <tr style="border-bottom: 1px solid #eee;">\n',
    '                            <td style="color: #666; font-size: 0.75rem;">{{ match.match.date|date:"j M" }}</td>\n',
    '                            <td style="text-align: left;">{% if match.is_home %}<strong>{{ team.name }}</strong> <span style="color:#999">vs</span> {{ match.opponent.name }}{% else %}{{ match.opponent.name }} <span style="color:#999">vs</span> <strong>{{ team.name }}</strong>{% endif %}</td>\n',
    '                            <td>{% if match.is_home %}<strong style="color: #333">{{ match.col_home_ppg }}</strong>{% else %}<span style="color:#aaa">{{ match.col_home_ppg }}</span>{% endif %}</td>\n',
    '                            <td>{% if not match.is_home %}<strong style="color: #333">{{ match.col_away_ppg }}</strong>{% else %}<span style="color:#aaa">{{ match.col_away_ppg }}</span>{% endif %}</td>\n',
    '                            <td style="vertical-align: middle;">\n',
    '                                <div style="display: flex; align-items: center; justify-content: start;">\n',
    '                                    <div style="background: #e0e0e0; height: 6px; width: 60px; border-radius: 3px; overflow: hidden; margin-right: 5px;">\n',
    '                                        <div class="js-width" data-width="{{ match.opp_strength_pct }}" style="height: 100%; background: #007bff;"></div>\n',
    '                                    </div>\n',
    '                                </div>\n',
    '                            </td>\n',
    '                        </tr>\n',
    '                        {% endfor %}\n'
]

lines[start_idx : end_idx+1] = new_block

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS: Loop block rewritten.")
