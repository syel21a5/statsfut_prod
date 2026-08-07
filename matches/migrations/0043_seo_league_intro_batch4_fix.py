# Fix: fill czech-republic/first-league (DB country is 'Czech-Republic', not 'Republica Tcheca')
import json
import os
from django.db import migrations
from django.conf import settings
from django.utils.text import slugify

def load_seo_texts(apps, schema_editor):
    League = apps.get_model('matches', 'League')
    json_path = os.path.join(settings.BASE_DIR, 'conteudo-lote4.json')
    if not os.path.exists(json_path):
        print("[!] conteudo-lote4.json nao encontrado")
        return
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    key = 'czech-republic/first-league'
    texts = data.get(key)
    if not texts:
        print("[!] chave", key, "nao existe no JSON")
        return

    found = None
    for league in League.objects.all():
        if slugify(league.country) == 'czech-republic' and slugify(league.name) == 'first-league':
            found = league
            break

    if found:
        found.intro_en = texts.get('en', '')
        found.intro_pt = texts.get('pt', '')
        found.intro_es = texts.get('es', '')
        found.intro_de = texts.get('de', '')
        found.save()
        print(f"[SEO] Liga atualizada (fix): {found.country} / {found.name}")
    else:
        print("[!] Liga tcheca nao encontrada no banco")

class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0042_seo_league_intro_batch4'),
    ]

    operations = [
        migrations.RunPython(load_seo_texts, reverse_code=migrations.RunPython.noop),
    ]
