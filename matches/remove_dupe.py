import os

file_path = r'c:\Users\VGR\.gemini\antigravity\scratch\betstats_python\matches\templates\matches\team_detail.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

search_str = "Comparison with past seasons (first {{ current_gp_comparison }} matches)"
start_tag = '<div class="ss-card" style="margin-bottom: 20px;">'

# Find all occurrences
indices = []
pos = 0
while True:
    idx = content.find(search_str, pos)
    if idx == -1:
        break
    indices.append(idx)
    pos = idx + 1

print(f"Found {len(indices)} occurrences of the search string.")

if len(indices) > 1:
    # We want to keep the FIRST one (which we inserted at line ~990)
    # and delete the SECOND one (which is the old one at line ~1190)
    
    # The 'indices' point to the text inside the div. We need to find the start of the div wrapping it.
    # The div starts a few lines before.
    second_occ_text_idx = indices[1]
    
    # Find the start of the card div leading up to this text
    # We search backwards from the text index
    block_start = content.rfind(start_tag, 0, second_occ_text_idx)
    
    if block_start != -1:
        print(f"Found block start at index {block_start}")
        
        # Now find the end of this block.
        # It ends after "With {{ standing.points }} points..." followed by </div>
        end_str = "With <strong>{{ standing.points }} points</strong> so far this season, {{ team.name }} have picked up..."
        end_text_idx = content.find(end_str, block_start)
        
        if end_text_idx != -1:
             # Find the closing </div> for the ss-card. 
             # There is a closing div for the inner div, then one for the card.
             # We can just look for the next "</div>" after end_text_idx, then another "</div>"
             
             close_div_1 = content.find("</div>", end_text_idx)
             close_div_2 = content.find("</div>", close_div_1 + 1)
             
             if close_div_2 != -1:
                 block_end = close_div_2 + 6 # include </div>
                 
                 print(f"Removing block from {block_start} to {block_end}")
                 
                 # reconstruct content
                 new_content = content[:block_start] + content[block_end:]
                 
                 # Clean up potential extra newlines if needed, but HTML is forgiving
                 
                 with open(file_path, 'w', encoding='utf-8') as f:
                     f.write(new_content)
                 print("Successfully removed duplicate block.")
             else:
                 print("Could not find closing div.")
        else:
            print("Could not find end text.")
    else:
        print("Could not find block start div.")
else:
    print("No duplicate found (or logic failed).")
