from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0032_alter_livematchsnapshot_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='home_shots_off_target',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='away_shots_off_target',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='home_possession',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='away_possession',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='home_dangerous_attacks',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='away_dangerous_attacks',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
