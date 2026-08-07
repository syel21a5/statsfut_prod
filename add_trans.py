import os

file_path = 'locale/pt_BR/LC_MESSAGES/django.po'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'msgid "Best Offences"' not in content:
    content += '\n\nmsgid "Best Offences"\nmsgstr "Melhores Ataques"\n'

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
