# Fix: batch 3 intro texts — match by URL slug (EN country) instead of slugify(DB name)
import json
import os
from django.db import migrations
from django.conf import settings
from django.utils.text import slugify

# EN URL slug -> PT name in DB (same as COUNTRY_TRANSLATIONS in matches/utils.py)
COUNTRY_MAP = {
    "england": "Inglaterra", "spain": "Espanha", "germany": "Alemanha",
    "italy": "Italia", "france": "Franca", "netherlands": "Holanda",
    "belgium": "Belgica", "portugal": "Portugal", "turkey": "Turquia",
    "greece": "Grecia", "austria": "Austria", "brazil": "Brasil",
    "argentina": "Argentina", "australia": "Australia", "switzerland": "Suica",
    "chile": "Chile", "czech-republic": "Republica Tcheca", "denmark": "Dinamarca",
    "finland": "Finlandia", "norway": "Noruega", "sweden": "Suecia",
    "poland": "Polonia", "ukraine": "Ucrania", "russia": "Russia",
    "japan": "Japao", "south-korea": "Coreia do Sul", "scotland": "Escocia",
    "mexico": "Mexico", "usa": "Estados Unidos", "ireland": "Irlanda",
    "wales": "Gales", "uruguay": "Uruguai", "paraguay": "Paraguai",
    "iceland": "Islandia", "ecuador": "Equador", "peru": "Peru",
    "south-america": "America do Sul",
    "america-do-sul": "America do Sul",
    "colombia": "Colombia"
}

def load_seo_texts(apps, schema_editor):
    League = apps.get_model('matches', 'League')
    json_path = os.path.join(settings.BASE_DIR, 'conteudo-lote3.json')
    if not os.path.exists(json_path):
        print(f"\n[!] JSON não encontrado: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    missing = []
    updated = 0
    all_leagues = list(League.objects.all())

    for slug_key, texts in data.items():
        try:
            c_slug, l_slug = slug_key.split('/')
        except ValueError:
            missing.append(slug_key)
            continue

        db_country = COUNTRY_MAP.get(c_slug, c_slug.replace('-', ' '))
        found = None
        for league in all_leagues:
            if slugify(league.country).replace('-', ' ') != slugify(db_country).replace('-', ' '):
                continue
            if slugify(league.name) == l_slug:
                found = league
                break

        if found:
            found.intro_en = texts.get('en', '')
            found.intro_pt = texts.get('pt', '')
            found.intro_es = texts.get('es', '')
            found.intro_de = texts.get('de', '')
            found.save()
            updated += 1
        else:
            missing.append(slug_key)

    print(f"\n[SEO] Ligas atualizadas (lote 3): {updated}")
    if missing:
        print(f"[!] Ligas do Lote 3 NÃO encontradas: {missing}")


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0040_seo_league_intro_batch2'),
    ]

    operations = [
        migrations.RunPython(load_seo_texts, reverse_code=migrations.RunPython.noop),
    ]
