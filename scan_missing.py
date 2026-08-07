import os
import re
import polib

def find_missing_translations():
    # Regex to capture translate tags correctly even with single quotes inside them, 
    # e.g., {% translate 'Overview of both teams\\' performance...' %}
    # We'll use a robust regex that matches either single or double quotes
    regex = re.compile(r'\{%\s*(?:translate|trans)\s+([\'"])(.*?)\1\s*(?:\|.*?)?%\}')
    
    missing = set()
    
    directories = ['matches/templates', 'members/templates', 'templates']
    
    for d in directories:
        if not os.path.exists(d):
            continue
        for root, dirs, files in os.walk(d):
            for file in files:
                if file.endswith('.html'):
                    path = os.path.join(root, file)
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = regex.findall(content)
                        for match in matches:
                            missing.add(match[1])
                            
    po = polib.pofile('locale/pt_BR/LC_MESSAGES/django.po')
    existing = set(entry.msgid for entry in po)
    
    really_missing = missing - existing
    
    print(f"Found {len(really_missing)} missing translations:")
    for r in sorted(list(really_missing)):
        print(f'"{r}"')

if __name__ == "__main__":
    find_missing_translations()
