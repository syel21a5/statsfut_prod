
from django.core.management.base import BaseCommand
from matches.models import Team, Match, League
from django.db.models import Q
from django.db import IntegrityError

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
            {'wrong': 'FC Salzburg',         'correct': 'Salzburg',            'country': 'Austria'},
            {'wrong': 'LASK',                'correct': 'LASK Linz',           'country': 'Austria'},
            {'wrong': 'SV Ried',             'correct': 'Ried',                'country': 'Austria'},
            {'wrong': 'WSG Tirol',           'correct': 'Tirol',               'country': 'Austria'},
            {'wrong': 'Grazer AK 1902',      'correct': 'Grazer AK',           'country': 'Austria'},
            {'wrong': 'GAK 1902',            'correct': 'Grazer AK',           'country': 'Austria'},
            {'wrong': 'FC Blau-Weiß Linz',   'correct': 'FC Blau Weiß Linz',   'country': 'Austria'},
            {'wrong': 'FC Blau Weiss Linz',  'correct': 'FC Blau Weiß Linz',   'country': 'Austria'},
            {'wrong': 'SV Grödig',           'correct': 'SV Grodig',           'country': 'Austria'},
            {'wrong': 'SK Sturm Graz',       'correct': 'Sturm Graz',          'country': 'Austria'},
            {'wrong': 'Wolfsberger AC',      'correct': 'Wolfsberger AC',      'country': 'Austria'}, # Just in case
            {'wrong': 'CASHPOINT SCR Altach','correct': 'Altach',              'country': 'Austria'},
            {'wrong': 'SCR Altach',          'correct': 'Altach',              'country': 'Austria'},
            {'wrong': 'SC Rheindorf Altach', 'correct': 'Altach',              'country': 'Austria'},
            {'wrong': 'TSV Hartberg',         'correct': 'Hartberg',            'country': 'Austria'},
            
            # BRASIL - Sincronizado com Server (ID 2)
            {'wrong': 'Vasco da Gama',       'correct': 'Vasco',               'country': 'Brasil'},
            {'wrong': 'Bragantino-SP',       'correct': 'Bragantino',          'country': 'Brasil'},
            {'wrong': 'RB Bragantino',       'correct': 'Bragantino',          'country': 'Brasil'},
            {'wrong': 'Red Bull Bragantino', 'correct': 'Bragantino',          'country': 'Brasil'},
            {'wrong': 'Atletico Mineiro',    'correct': 'Atletico-MG',         'country': 'Brasil'},
            {'wrong': 'Atlético Mineiro',    'correct': 'Atletico-MG',         'country': 'Brasil'},
            {'wrong': 'Athletico Paranaense','correct': 'Athletico-PR',        'country': 'Brasil'},
            {'wrong': 'Athletico',           'correct': 'Athletico-PR',        'country': 'Brasil'},
            {'wrong': 'Grêmio',              'correct': 'Gremio',              'country': 'Brasil'},
            {'wrong': 'Sao Paulo',           'correct': 'São Paulo',           'country': 'Brasil'},
            {'wrong': 'Ceará',               'correct': 'Ceara',               'country': 'Brasil'},
            # ARGENTINA - Sincronizado com SofaScore
            {'wrong': 'Estudiantes de La Plata', 'correct': 'Estudiantes L.P.',    'country': 'Argentina'},
            {'wrong': 'Vélez Sarsfield',         'correct': 'Velez Sarsfield',     'country': 'Argentina'},
            {'wrong': 'CA Talleres',             'correct': 'Talleres Cordoba',    'country': 'Argentina'},
            {'wrong': 'CA Lanús',                'correct': 'Lanus',               'country': 'Argentina'},
            {'wrong': 'CA Independiente',        'correct': 'Independiente',       'country': 'Argentina'},
            {'wrong': 'Club Atlético Unión de Santa Fe', 'correct': 'Union de Santa Fe', 'country': 'Argentina'},
            {'wrong': 'Instituto De Córdoba',    'correct': 'Instituto',           'country': 'Argentina'},
            {'wrong': 'Club Atlético Platense',  'correct': 'Platense',            'country': 'Argentina'},
            {'wrong': 'Gimnasia y Esgrima Mendoza', 'correct': 'Gimnasia Mendoza', 'country': 'Argentina'},
            {'wrong': "Newell's Old Boys",       'correct': 'Newells Old Boys',    'country': 'Argentina'},
            {'wrong': 'Deportivo Riestra',       'correct': 'Dep. Riestra',        'country': 'Argentina'},
            {'wrong': 'Independiente Rivadavia', 'correct': 'Ind. Rivadavia',      'country': 'Argentina'},
            {'wrong': 'Argentinos Juniors',      'correct': 'Argentinos Jrs',      'country': 'Argentina'},
            
            # AUSTRALIA
            {'wrong': 'Newcastle Jets FC',       'correct': 'Newcastle Jets',      'country': 'Australia'},
            {'wrong': 'WS Wanderers',            'correct': 'Western Sydney Wanderers', 'country': 'Australia'},
            {'wrong': 'Club Atlético Belgrano',  'correct': 'Belgrano',            'country': 'Argentina'},
            {'wrong': 'Gimnasia y Esgrima',      'correct': 'Gimnasia L.P.',       'country': 'Argentina'},
            {'wrong': 'Huracán',                 'correct': 'Huracan',             'country': 'Argentina'},
            {'wrong': 'Atlético Tucumán',        'correct': 'Atl. Tucuman',        'country': 'Argentina'},
            {'wrong': 'Sarmiento',               'correct': 'Sarmiento Junin',     'country': 'Argentina'},
            {'wrong': 'Estudiantes de Río Cuarto', 'correct': 'Estudiantes Rio Cuarto', 'country': 'Argentina'},
            {'wrong': 'Central Córdoba',         'correct': 'Central Cordoba',     'country': 'Argentina'},
            
            # AUSTRALIA - Sincronizado com Server (ID 21)
            {'wrong': 'Newcastle Jets FC',    'correct': 'Newcastle Jets',      'country': 'Australia'},
            {'wrong': 'Wellington Phoenix FC','correct': 'Wellington Phoenix',   'country': 'Australia'},
            {'wrong': 'Melbourne City FC',   'correct': 'Melbourne City',      'country': 'Australia'},
            
            # BELGICA
            {'wrong': 'Club Brugge KV',      'correct': 'Club Brugge',         'country': 'Belgica'},
            {'wrong': 'Standard Liège',      'correct': 'Standard Liege',      'country': 'Belgica'},
            {'wrong': 'Royal Antwerp FC',    'correct': 'Antwerp',             'country': 'Belgica'},
            {'wrong': 'Royale Union Saint-Gilloise', 'correct': 'Union St. Gilloise', 'country': 'Belgica'},
            {'wrong': 'KAA Gent',            'correct': 'Gent',                'country': 'Belgica'},
            {'wrong': 'KRC Genk',            'correct': 'Genk',                'country': 'Belgica'},
            {'wrong': 'RC Sporting Charleroi', 'correct': 'Charleroi',          'country': 'Belgica'},
            {'wrong': 'OH Leuven',           'correct': 'Oud-Heverlee Leuven', 'country': 'Belgica'},
            {'wrong': 'Saint-Truidense VV',  'correct': 'Sint-Truidense VV',   'country': 'Belgica'},

            # SUICA
            {'wrong': 'BSC Young Boys',      'correct': 'Young Boys',          'country': 'Suica'},
            {'wrong': 'FC St. Gallen 1879',  'correct': 'St. Gallen',          'country': 'Suica'},
            {'wrong': 'Grasshopper Club Zürich', 'correct': 'Grasshoppers',     'country': 'Suica'},
            {'wrong': 'FC Lausanne-Sport',   'correct': 'Lausanne',            'country': 'Suica'},
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
            self.stdout.write(f"Merging '{wrong_team.name}' into '{correct_team.name}'...")
            
            # Update Matches (Home) - also fix league if needed
            for m in Match.objects.filter(home_team=wrong_team):
                # Check if duplicate already exists
                existing = Match.objects.filter(
                    home_team=correct_team,
                    away_team=m.away_team,
                    league=correct_team.league,
                    date__date=m.date.date() if m.date else None
                ).first()
                
                if existing:
                    # Keep the one with more data (scores, status)
                    if existing.home_score is None and m.home_score is not None:
                        existing.home_score = m.home_score
                        existing.away_score = m.away_score
                        existing.status = m.status
                        existing.save()
                    m.delete()
                else:
                    m.home_team = correct_team
                    if m.league != correct_team.league:
                        m.league = correct_team.league
                    try:
                        m.save()
                    except IntegrityError:
                        m.delete()
                    
            # Update Matches (Away) - also fix league if needed
            for m in Match.objects.filter(away_team=wrong_team):
                existing = Match.objects.filter(
                    home_team=m.home_team,
                    away_team=correct_team,
                    league=correct_team.league,
                    date__date=m.date.date() if m.date else None
                ).first()
                
                if existing:
                    if existing.home_score is None and m.home_score is not None:
                        existing.home_score = m.home_score
                        existing.away_score = m.away_score
                        existing.status = m.status
                        existing.save()
                    m.delete()
                else:
                    m.away_team = correct_team
                    if m.league != correct_team.league:
                        m.league = correct_team.league
                    try:
                        m.save()
                    except IntegrityError:
                        m.delete()
            
            # Delete wrong team
            wrong_team.delete()
