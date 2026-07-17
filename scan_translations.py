import re
import os

# 1. Collect all translate strings from templates
template_dir = 'matches/templates/matches'
translate_pattern = re.compile(r'\{%\s*translate\s+"([^"]+)"\s*%\}')
trans_pattern2 = re.compile(r'\{%\s*trans\s+"([^"]+)"\s*%\}')

all_strings = {}
for root, dirs, files in os.walk(template_dir):
    for fname in files:
        if fname.endswith('.html'):
            fpath = os.path.join(root, fname)
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            for m in translate_pattern.finditer(content):
                s = m.group(1)
                if s not in all_strings:
                    all_strings[s] = []
                all_strings[s].append(fname)
            for m in trans_pattern2.finditer(content):
                s = m.group(1)
                if s not in all_strings:
                    all_strings[s] = []
                all_strings[s].append(fname)

# Also scan members templates
for tdir in ['members/templates/members', 'templates']:
    if os.path.exists(tdir):
        for root, dirs, files in os.walk(tdir):
            for fname in files:
                if fname.endswith('.html'):
                    fpath = os.path.join(root, fname)
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    for m in translate_pattern.finditer(content):
                        s = m.group(1)
                        if s not in all_strings:
                            all_strings[s] = []
                        all_strings[s].append(fname)
                    for m in trans_pattern2.finditer(content):
                        s = m.group(1)
                        if s not in all_strings:
                            all_strings[s] = []
                        all_strings[s].append(fname)

# 2. Load django.po and find all msgid strings
with open('locale/pt_BR/LC_MESSAGES/django.po', 'r', encoding='utf-8') as f:
    po_content = f.read()

# Find all msgid/msgstr pairs (both active and commented out ~)
po_entries = re.findall(r'(?:^|\n)msgid "([^"]+)"\s*\nmsgstr "([^"]*)"', po_content)
translated = {}
for msgid, msgstr in po_entries:
    if msgstr:  # Only count as translated if msgstr is not empty
        translated[msgid] = msgstr

# Also check for multiline msgstr
po_entries_ml = re.findall(r'(?:^|\n)msgid "([^"]+)"\s*\nmsgstr ""\s*\n"([^"]+)"', po_content)
for msgid, msgstr in po_entries_ml:
    if msgstr:
        translated[msgid] = msgstr

# 3. Find missing
missing = []
for s in sorted(all_strings.keys()):
    if s not in translated:
        missing.append((s, list(set(all_strings[s]))))

print(f'Total translate strings in templates: {len(all_strings)}')
print(f'Total translated in .po: {len(translated)}')
print(f'Missing translations: {len(missing)}')
print()
for s, files in missing:
    print(f'MISSING: "{s}"')
    print(f'  Files: {", ".join(files)}')
    print()
