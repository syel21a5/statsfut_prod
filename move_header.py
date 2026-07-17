import os
import sys

file_path = 'matches/templates/matches/h2h_detail.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "            <!-- Matchup Header Card -->"
end_marker = "            <!-- H2H SEO Dynamic Text -->"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Could not find markers")
    sys.exit(1)

# Extract the header card block
header_block = content[start_idx:end_idx]

# Remove it from its original place
new_content = content[:start_idx] + content[end_idx:]

# Insert it right before the <style> block of premium-tabs
insert_marker = "            <style>\n                .premium-tabs"
insert_idx = new_content.find(insert_marker)

if insert_idx == -1:
    print("Could not find insert marker")
    sys.exit(1)

new_content = new_content[:insert_idx] + header_block + new_content[insert_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Successfully moved header card!")
