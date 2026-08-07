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
    
    second_occ_text_idx = indices[1]
    
    # 1. Find block start (search backwards for ss-card)
    block_start = content.rfind(start_tag, 0, second_occ_text_idx)
    
    if block_start != -1:
        print(f"Found block start at index {block_start}")
        
        # 2. Find </table> after the text
        table_end = content.find("</table>", second_occ_text_idx)
        
        if table_end != -1:
            # 3. From here, we expect 2 footer divs and then the closing div.
            # Footer 1: <div>...</div>
            # Footer 2: <div>...</div>
            # Closing card: </div>
            
            # We need to find the 3rd </div> after table_end
            
            current_pos = table_end
            closing_divs_found = 0
            block_end = -1
            
            while closing_divs_found < 3:
                next_div = content.find("</div>", current_pos)
                if next_div == -1:
                    break
                current_pos = next_div + 6 # move past </div>
                closing_divs_found += 1
                block_end = current_pos
            
            if closing_divs_found == 3:
                print(f"Found block end at {block_end}")
                 # reconstruct content
                new_content = content[:block_start] + content[block_end:]
                 
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print("Successfully removed duplicate block (v2).")
            else:
                print(f"Only found {closing_divs_found} closing divs. Safety abort.")
                
        else:
             print("Could not find table end.")
    else:
        print("Could not find block start div.")
else:
    print("No duplicate found (or logic failed).")
