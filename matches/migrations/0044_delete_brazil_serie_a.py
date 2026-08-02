from django.db import migrations

def delete_duplicate_serie_a(apps, schema_editor):
    League = apps.get_model('matches', 'League')
    # Deleta liga Serie A (id 84) do Brasil, se existir
    League.objects.filter(country='Brasil', name='Serie A').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0043_seo_league_intro_batch4_fix'),
    ]

    operations = [
        migrations.RunPython(delete_duplicate_serie_a, reverse_code=migrations.RunPython.noop),
    ]
