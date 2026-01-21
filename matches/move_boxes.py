
import os

file_path = r'c:\Users\VGR\.gemini\antigravity\scratch\betstats_python\matches\templates\matches\team_detail.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# identify start and end lines of the block to move
start_marker = "<!-- Current Streaks & Sequences -->"
end_marker = "</style>"
# We look for the end marker occurring AFTER the start marker

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if start_marker in line:
        start_idx = i
        break

if start_idx != -1:
    # Find the end style tag after start_idx
    for i in range(start_idx, len(lines)):
        if end_marker in lines[i]:
            end_idx = i
            break

# Identify insertion point
# We want to insert AFTER the "Comparison with Past Seasons Box"
# The box ends before "<!-- End Left Group -->"
insert_marker_comment = "<!-- End Left Group -->"
insert_idx = -1

for i, line in enumerate(lines):
    if insert_marker_comment in line:
        # We want to insert BEFORE this line (which is the closing div of the group)
        # But wait, looking at the file view:
        # 1059:             </div>
        # 1060: 
        # 1061:         </div> <!-- End Left Group -->
        # We want to be INSIDE the Left Group, so before the </div> that closes the Left Group.
        insert_idx = i 
        break

if start_idx != -1 and end_idx != -1 and insert_idx != -1:
    print(f"Found block to move: {start_idx} to {end_idx}")
    print(f"Found insertion point: {insert_idx}")
    
    # Extract block
    block_to_move = lines[start_idx:end_idx+1]
    
    # Remove block from original location (careful with indices if insertion point is AFTER removal)
    # In this case:
    # Insertion point is around 1061
    # Removal point is around 1190
    # So removal is AFTER insertion. This makes it easier.
    
    # We can effectively construct the new list
    
    # Lines before insertion
    new_lines = lines[:insert_idx]
    
    # The block
    # Add a newline for spacing
    new_lines.append("\n")
    new_lines.extend(block_to_move)
    new_lines.append("\n")
    
    # Lines between insertion and removal start
    new_lines.extend(lines[insert_idx:start_idx])
    
    # Lines after removal end
    new_lines.extend(lines[end_idx+1:])
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("Successfully moved the stats boxes.")

else:
    print("Could not find markers.")
    print(f"Start: {start_idx}, End: {end_idx}, Insert: {insert_idx}")
