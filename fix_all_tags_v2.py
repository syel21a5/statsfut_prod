
import os
import re

file_path = r'C:\Users\VGR\.gemini\antigravity\scratch\betstats_python\matches\templates\matches\team_detail.html'

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    
    # Pattern 1: Tag starts on one line and ends on another
    # Case A: {% ... \n ... %}
    # We want to collapse whitespace around the newline
    
    # Regex to find {% followed by content, newline, content, %}
    # We use dotall (?s) so . matches newline, but we want to be careful not to match too much.
    # Instead, let's iterate.
    
    # Fix {% ... %}
    # We look for '{%' that doesn't have a matching '%}' on the same line?
    # Or just replace any sequence of '{%\s*(.*?)\s*%}' where matches across lines.
    
    # Let's try a robust regex that matches balanced {% ... %} even with newlines
    # But we want to REMOVE the newlines inside the tag.
    
    def replacer(match):
        text = match.group(0)
        if '\n' in text:
            # Replace newline and surrounding whitespace with a single space
            cleaned = re.sub(r'\s*\n\s*', ' ', text)
            print(f"Fixed split tag: {text!r} -> {cleaned!r}")
            return cleaned
        return text

    # Regex for {% ... %}
    # We assume tags don't nest inside tags.
    pattern_block = r'\{%.*?%\}'
    content = re.sub(pattern_block, replacer, content, flags=re.DOTALL)
    
    # Regex for {{ ... }}
    pattern_var = r'\{\{.*?\}\}'
    content = re.sub(pattern_var, replacer, content, flags=re.DOTALL)
    
    # Specific fix for the case where {% is at end of line and %} at start of next (or middle)
    # The above regex might fail if '.*?' doesn't match greedy enough or if there are multiple tags.
    # Actually '.*?' is non-greedy.
    
    # Let's doubly ensure we caught the specific cases seen
    # Case: ... {{ i }}{% if i == "4" \n %}+{% endif %}
    # The problem: The first regex matches `{% if i == "4" \n %}` and fixes it?
    # Yes, it should.
    
    if content != original_content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("SUCCESS: File updated with tag fixes.")
    else:
        print("NO CHANGE: No split tags found (or regex failed to match).")

fix_file(file_path)
