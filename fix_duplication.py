import os

file_path = 'matches/templates/matches/team_detail.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

marker = '<!-- Points Per Game / Run-in Analysis -->'
first_idx = content.find(marker)
second_idx = content.find(marker, first_idx + 1)

if second_idx != -1:
    print(f"Found duplicate at index {second_idx}")
    # Find the end of this block. It ends before <script src=...
    # Actually, we know it ends at </div> before <script
    script_idx = content.find('<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>', second_idx)
    
    if script_idx != -1:
        # The block ends just before script_idx. 
        # There are some closing divs.
        # Let's verify the content to be deleted.
        to_delete = content[second_idx:script_idx]
        print(f"Deleting {len(to_delete)} chars.")
        # print(to_delete[:100])
        
        # We need to be careful not to delete too much.
        # The block ends with </div> </div> </div> </div> ?
        # In the file view, the duplicate block was immediately followed by <script>.
        # So deleting everything from marker to script_idx should be safe, 
        # provided we leave the necessary closing divs for the main layout IF they were part of the duplicate.
        # Wait, the duplicate block ENDS with </div> which closes the card.
        # Does it contain extra closing divs?
        # The duplicate was inserted at 1559.
        # The original code had:
        # 1634: </div> <!-- closes container? -->
        # 1635: </div> <!-- closes row? -->
        # 1636: </div> <!-- closes wrapper? -->
        
        # Taking a look at Step 325:
        # 1707: </div> (closes card)
        # 1708: </div>
        # 1709: </div>
        # 1710: </div>
        # 1712: <script...
            
        # The matched block starts with a card.
        # If I delete from marker to script_idx, I might delete lines 1708, 1709, 1710.
        # Are those lines part of the duplicate?
        # The duplicate was inserted *in place of* "Scoring Conceding".
        # "Scoring Conceding" was followed by 3 closing divs.
        
        # If I delete match->script, I delete the closing divs too.
        # If the duplicate *included* those closing divs, then I should delete them.
        # But wait, the Left Group *closing div* (Line 1424) was where I inserted the NEW Copy.
        
        # The OLD copy (duplicate) is at the bottom.
        # If I delete it, I might break the layout closing tags.
        # I need to know if the duplicate block *contains* the closing tags or if they are after it.
        
        # Let's look at the "wrongly inserted" text from Step 284.
        # It ends with `</div>` (one div).
        # So the extra closing divs (1708-1710) are NOT part of the inserted block?
        # Wait, Step 284 replacement content ends with `</div> ` (lines 1631).
        # It replaced a block that was `</div> ... </div>`.
        
        # I suspect the 3 closing divs at 1708-1710 are essential for the page footer.
        # The duplicate block is JUST the `ss-card`.
        # So I should find the LAST `</div>` relative to the marker, but before the script?
        # NO, the duplicate block is the `ss-card`. It has correct closing.
        # So I should delete up to the closing `</div>` of that card.
        
        # Heuristic: The block starts with <div class="ss-card"...
        # It contains standard HTML.
        # I can count opening/closing divs?
        # Or I can just search for the *text* of the closing `</div>` lines?
        
        # Let's try to identify the `ss-card` end.
        # The card ends with:
        # ...
        #    </div>
        # </div>
        # (Div for "view opponents" button, then div for card body, then div for card?)
        
        # Let's look at Step 325 again.
        # 1701: <div style="text-align: center...
        # 1705: </div> (closes text-align)
        # 1706: </div> (closes font-size 0.8rem...)
        # 1707: </div> (closes ss-card)
        
        # So I should delete from `marker` up to line 1707 `</div>` + newline.
        # I should LEAVE lines 1708, 1709, 1710.
        
        # How to find line 1707 programmatically?
        # Search for `view opponents PPG values for all teams</a>`
        # Then find the next 3 `</div>`s?
        
        anchor_text = 'View opponents PPG values for all teams</a>'
        anchor_idx = content.find(anchor_text, second_idx)
        if anchor_idx != -1:
            # Find the closing div of the card
            # The structure is:
            # ... </a>
            # </div> (closes button wrapper)
            # </div> (closes padding wrapper)
            # </div> (closes card)
            
            end_idx = anchor_idx
            for _ in range(3):
                end_idx = content.find('</div>', end_idx + 1)
            
            # end_idx points to the start of the 3rd </div>.
            # We want to include it in deletion (it's the end of the duplicate card).
            end_idx += 6 # len('</div>')
            
            # Delete from second_idx to end_idx
            new_content = content[:second_idx] + content[end_idx:]
            
            with open(file_path, 'w', encoding='utf-8') as f_out:
                f_out.write(new_content)
            print("Successfully deleted duplicate block.")
            
    else:
        print("Script tag not found, unsafe to proceed.")
else:
    print("Duplicate not found.")
