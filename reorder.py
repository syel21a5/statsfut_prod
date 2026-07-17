import os
import re

html_file = r'i:\GitHub\statsfut\statsfut\matches\templates\matches\h2h_detail.html'

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Instead of re.DOTALL which might be failing, let's find start and end strings.
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

# 1. Key Probabilities
# Starts at "<!-- Key Probabilities -->"
# Ends before "<!-- Recent H2H Matches -->"
idx_kp = content.find("<!-- Key Probabilities -->")
idx_rh = content.find("<!-- Recent H2H Matches -->")
b1 = ""
if idx_kp != -1 and idx_rh != -1:
    b1 = content[idx_kp:idx_rh]
    content = content[:idx_kp] + content[idx_rh:]
else:
    print("Block 1 not found")

# 2. Fallback H2H (Estimated Probabilities)
# Starts at "{% if fallback_h2h %}" right before "Estimated Probabilities"
# Ends at "{% endif %}" right after "</div>\n            </div>\n            {% endif %}"
b2 = extract_block("{% if fallback_h2h %}", "{% endif %}\n")
if not b2:
    print("Block 2 not found")

# 3. Detailed Goals Analysis Grid and Comparison with league average
# Starts at "<!-- NEW: Detailed Goals Analysis Grid -->"
# Ends before "<!-- Aba 3: Sequências & Avançadas -->" or a div closing before it.
idx_dg = content.find("<!-- NEW: Detailed Goals Analysis Grid -->")
idx_a3 = content.find("<!-- Aba 3: Sequências & Avançadas -->")
b3 = ""
if idx_dg != -1 and idx_a3 != -1:
    # Actually, we should probably extract up to the end of the div holding them.
    # Let's just use string find up to the exact comment.
    b3 = content[idx_dg:idx_a3]
    content = content[:idx_dg] + content[idx_a3:]
else:
    print("Block 3 not found")

# Now append to Aba 3
aba3_marker = '<!-- Aba 3: Sequências & Avançadas -->\n                <div class="tab-pane fade" id="avancadas" role="tabpanel" aria-labelledby="avancadas-tab">\n                    <div class="row g-4 mb-4">\n                        <div class="col-12">\n'

aba3_content = b1 + "\n" + b3 + "\n" + b2

content = content.replace(aba3_marker, aba3_marker + aba3_content)

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
