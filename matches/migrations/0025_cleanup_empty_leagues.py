from django.db import migrations

def delete_empty_leagues(apps, schema_editor):
    League = apps.get_model('matches', 'League')
    # Filter for leagues that have 0 matches and delete them
    # To be extremely safe, we do count() or filter.
    for league in League.objects.all():
        if league.matches.count() == 0:
            print(f"Deleting empty league: {league.name} ({league.country})")
            league.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0024_alter_betticket_ticket_type_delete_matchmarketodd'),
    ]

    operations = [
        migrations.RunPython(delete_empty_leagues),
    ]
