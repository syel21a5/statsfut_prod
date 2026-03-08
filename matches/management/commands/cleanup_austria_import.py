from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from django.db.models import Count

class Command(BaseCommand):
    help = "Clean up and merge duplicate teams and seasons for Austria import"

    def handle(self, *args, **options):
        # 1. Fix Season Duplicates
        years = Season.objects.values('year').annotate(c=Count('id')).filter(c__gt=1)
        for entry in years:
            year = entry['year']
            seasons = list(Season.objects.filter(year=year).order_by('id'))
            primary_season = seasons[0]
            extra_seasons = seasons[1:]
            
            for extra in extra_seasons:
                self.stdout.write(f"Merging Season {year} (ID {extra.id} -> {primary_season.id})")
                Match.objects.filter(season=extra).update(season=primary_season)
                extra.delete()

        # 2. Fix Austria Team Duplicates
        league = League.objects.filter(country='Austria').first()
        if not league:
            self.stdout.write("League not found.")
            return

        # Mapping: Duplicate Name -> Canonical Name
        merges = {
            'SK Rapid Wien': 'Rapid Vienna',
            'SK Sturm Graz': 'Sturm Graz',
            'SK Austria Klagenfurt': 'Austria Klagenfurt',
            'SKN St. Pölten': 'SKN St. Polten',
            'LASK Linz': 'LASK',
            'SCR Altach': 'SC Rheindorf Altach',
            'SV Mattersburg': 'SC Mattersburg',
            'Admira Wacker': 'Admira Wacker Modling',
            'FC Admira Wacker': 'Admira Wacker Modling',
            'FC Blau-Weiß Linz': 'Blau-Weiss Linz',
            'FC Blau Weiss Linz': 'Blau-Weiss Linz',
            'Blau-Weiß Linz': 'Blau-Weiss Linz',
            'Altach': 'SC Rheindorf Altach',
            'R. Altach': 'SC Rheindorf Altach',
            'Mattersburg': 'SC Mattersburg',
            'Ried': 'SV Ried',
            'St. Polten': 'SKN St. Polten',
            'Tirol': 'WSG Tirol',
            'W. Innsbruck': 'Wacker Innsbruck',
            'FK Austria Wien': 'Austria Vienna',
            'Grazer AK': 'Grazer AK 1902',
            'FC Groedig': 'FC Grodig',
            'SV Grödig': 'FC Grodig',
            'SV Groedig': 'FC Grodig',
            'Hartberg': 'TSV Hartberg',
            'RB Salzburg': 'Red Bull Salzburg',
            'Austria Wien': 'Austria Vienna',
            'Rapid Wien': 'Rapid Vienna',
            'Grazer AK': 'Grazer AK 1902',
            'FC Blau Weiß Linz': 'Blau-Weiss Linz',
            'a.e.t. (1-1, 0-0)  Austria Lustenau': None,
            'Austria Wien            v FC Admira Wacker': None,
        }

        for dupe_name, canonical_name in merges.items():
            canonical_team = Team.objects.filter(name=canonical_name, league=league).first()
            dupe_team = Team.objects.filter(name=dupe_name, league=league).first()

            if dupe_team and canonical_team and dupe_team != canonical_team:
                self.stdout.write(f"Merging Team '{dupe_name}' into '{canonical_name}'")
                Match.objects.filter(home_team=dupe_team).update(home_team=canonical_team)
                Match.objects.filter(away_team=dupe_team).update(away_team=canonical_team)
                dupe_team.delete()
            elif dupe_team and not canonical_team:
                self.stdout.write(f"Renaming Team '{dupe_name}' to '{canonical_name}'")
                dupe_team.name = canonical_name
                dupe_team.save()

        self.stdout.write(self.style.SUCCESS("Cleanup complete."))
