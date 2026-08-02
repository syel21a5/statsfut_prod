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
    "chile": "Chile", "czech-republic": "Czech-Republic", "denmark": "Dinamarca",
    "finland": "Finlandia", "norway": "Noruega", "sweden": "Suecia",
    "poland": "Polonia", "ukraine": "Ucrania", "russia": "Russia",
    "japan": "Japao", "south-korea": "Coreia do Sul", "scotland": "Escocia",
    "mexico": "Mexico", "usa": "Estados Unidos", "ireland": "Irlanda",
    "wales": "Gales", "uruguay": "Uruguai", "paraguay": "Paraguai",
    "iceland": "Islandia", "ecuador": "Equador", "peru": "Peru",
    "south-america": "America do Sul",
}

def load_seo_country_texts(apps, schema_editor):
    Country = apps.get_model('matches', 'Country')
    json_path = os.path.join(settings.BASE_DIR, 'conteudo-paises.json')
    if not os.path.exists(json_path):
        print(f"\n[!] JSON não encontrado: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    missing = []
    updated = 0

    for slug_key, texts in data.items():
        db_country_name = COUNTRY_MAP.get(slug_key, slug_key.replace('-', ' ').title())
        
        country, created = Country.objects.get_or_create(name=db_country_name)
        
        country.intro_en = texts.get('en', '')
        country.intro_pt = texts.get('pt', '')
        country.intro_es = texts.get('es', '')
        country.intro_de = texts.get('de', '')
        country.save()
        
        updated += 1
        print(f"[{'NEW' if created else 'UPD'}] {db_country_name}")

    print(f"\n[SEO] Países atualizados: {updated}")


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0044_delete_brazil_serie_a'),
    ]

    operations = [
        migrations.RunPython(load_seo_country_texts, reverse_code=migrations.RunPython.noop),
    ]
