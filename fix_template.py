
import os

file_path = r'C:\Users\VGR\.gemini\antigravity\scratch\betstats_python\matches\templates\matches\team_detail.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Identify the bad block range (1523 to 1531, 0-indexed is 1522 to 1530)
# Let's target lines by index directly since we know them from grep/view
# 0-indexed:
# Line 1523 is index 1522
# Line 1531 is index 1530

start_idx = 1522
end_idx = 1530 # Inclusive of the last line to remove

# Verify we are looking at the right lines
expected_first = '<td style="text-align: left;">{% if match.is_home %}<strong>{{ team.name }}</strong> <span'
actual_first = lines[start_idx].strip()

if not actual_first.startswith('<td style="text-align: left;">{% if match.is_home %}'):
    print(f"ERROR: Line {start_idx+1} does not match expected start.")
    print(f"Expected start: {expected_first}")
    print(f"Actual: {actual_first}")
    exit(1)

# Construct new lines
new_lines = [
    '                            <td style="text-align: left;">{% if match.is_home %}<strong>{{ team.name }}</strong> <span style="color:#999">vs</span> {{ match.opponent.name }}{% else %}{{ match.opponent.name }} <span style="color:#999">vs</span> <strong>{{ team.name }}</strong>{% endif %}</td>\n',
    '                            <td>{% if match.is_home %}<strong style="color: #333">{{ match.col_home_ppg }}</strong>{% else %}<span style="color:#aaa">{{ match.col_home_ppg }}</span>{% endif %}</td>\n',
    '                            <td>{% if not match.is_home %}<strong style="color: #333">{{ match.col_away_ppg }}</strong>{% else %}<span style="color:#aaa">{{ match.col_away_ppg }}</span>{% endif %}</td>\n'
]

# Replace
# We are replacing 9 lines (1523 to 1531) with 3 lines
lines[start_idx : end_idx+1] = new_lines

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS: File updated.")
