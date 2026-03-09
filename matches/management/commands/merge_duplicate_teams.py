
from django.core.management.base import BaseCommand
from matches.models import Team, Match, League
from django.db.models import Q

class Command(BaseCommand):
    help = 'Merge duplicate teams (e.g. "Rapid Vienna" -> "Rapid Wien") and cleanup leagues'

    def handle(self, *args, **options):
        self.stdout.write("Starting team merge process...")
        
        # Mappings: { 'Wrong Name': 'Correct Name' }
        # Country is optional filter
        merge_map = [
            # AUSTRIA - Sincronizado com os nomes do Servidor (ID 44)
            {'wrong': 'Rapid Vienna',        'correct': 'Rapid Wien',          'country': 'Austria'},
            {'wrong': 'SK Rapid Wien',       'correct': 'Rapid Wien',          'country': 'Austria'},
            {'wrong': 'Austria Vienna',      'correct': 'Austria Wien',        'country': 'Austria'},
            {'wrong': 'FK Austria Wien',     'correct': 'Austria Wien',        'country': 'Austria'},
            {'wrong': 'Red Bull Salzburg',   'correct': 'Salzburg',            'country': 'Austria'},
            {'wrong': 'LASK',                'correct': 'LASK Linz',           'country': 'Austria'},
            {'wrong': 'SV Ried',             'correct': 'Ried',                'country': 'Austria'},
            {'wrong': 'WSG Tirol',           'correct': 'Tirol',               'country': 'Austria'},
            {'wrong': 'Grazer AK 1902',      'correct': 'Grazer AK',           'country': 'Austria'},
            {'wrong': 'FC Blau-Weiß Linz',   'correct': 'FC Blau Weiß Linz',   'country': 'Austria'},
            {'wrong': 'FC Blau Weiss Linz',  'correct': 'FC Blau Weiß Linz',   'country': 'Austria'},
            {'wrong': 'SV Grödig',           'correct': 'SV Grodig',           'country': 'Austria'},
            
            # BRASIL - Sincronizado com Server (ID 2)
            {'wrong': 'Vasco da Gama',       'correct': 'Vasco',               'country': 'Brasil'},
            {'wrong': 'Bragantino-SP',       'correct': 'Bragantino',          'country': 'Brasil'},
            {'wrong': 'RB Bragantino',       'correct': 'Bragantino',          'country': 'Brasil'},
            {'wrong': 'Atletico Mineiro',    'correct': 'Atletico-MG',         'country': 'Brasil'},
            {'wrong': 'Athletico Paranaense','correct': 'Athletico-PR',         'country': 'Brasil'},
            {'wrong': 'Grêmio',              'correct': 'Gremio',              'country': 'Brasil'},
            {'wrong': 'Sao Paulo',           'correct': 'São Paulo',           'country': 'Brasil'},
            {'wrong': 'Ceará',               'correct': 'Ceara',               'country': 'Brasil'},
        ]

        for item in merge_map:
            self.merge_teams(item['wrong'], item['correct'], item.get('country'))

        self.stdout.write(self.style.SUCCESS("Cleanup and merge process completed."))

    def merge_teams(self, wrong_name, correct_name, country=None):
        # Find correct team
        query = Q(name=correct_name)
        if country:
            query &= Q(league__country__icontains=country)
        
        correct_team = Team.objects.filter(query).first()
        
        if not correct_team:
            return

        # Find wrong team(s)
        w_query = Q(name=wrong_name)
        if country:
            w_query &= Q(league__country__icontains=country)
        
        # Exclude the correct team itself if names are similar/same
        wrong_teams = Team.objects.filter(w_query).exclude(id=correct_team.id)

        for wrong_team in wrong_teams:
            if wrong_team.league != correct_team.league:
                self.stdout.write(f"Skipping merge: '{wrong_team}' and '{correct_team}' are in different leagues.")
                continue

            self.stdout.write(f"Merging '{wrong_team.name}' into '{correct_team.name}'...")
            
            # Update Matches (Home)
            Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
            # Update Matches (Away)
            Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
            
            # Delete wrong team
            wrong_team.delete()
