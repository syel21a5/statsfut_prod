from django.core.management.base import BaseCommand
from django.db.models import Count
from matches.models import Team, Match, League

class Command(BaseCommand):
    help = 'Mescla times duplicados com nomes diferentes (ex: RCD Espanyol de Barcelona -> Espanol)'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando mesclagem de times duplicados...")

        # Mapa de nomes errados (API) para nomes certos (DB)
        # Copiado e adaptado do update_live_matches.py
        name_mapping = {
            # La Liga
            'RCD Espanyol de Barcelona': 'Espanol',
            'RC Celta de Vigo': 'Celta',
            'Villarreal CF': 'Villarreal',
            'Getafe CF': 'Getafe',
            'Sevilla FC': 'Sevilla',
            'Deportivo Alavés': 'Alaves',
            'Real Sociedad de Fútbol': 'Sociedad',
            'Club Atlético de Madrid': 'Ath Madrid',
            'Athletic Club': 'Ath Bilbao',
            'Real Betis Balompié': 'Betis',
            'RCD Mallorca': 'Mallorca',
            'Valencia CF': 'Valencia',
            'Girona FC': 'Girona',
            'Real Madrid CF': 'Real Madrid',
            'Levante UD': 'Levante',
            'Elche CF': 'Elche',
            'Cádiz CF': 'Cadiz',
            'Real Valladolid CF': 'Valladolid',
            'CA Osasuna': 'Osasuna',
            'Rayo Vallecano de Madrid': 'Rayo Vallecano',
            'UD Las Palmas': 'Las Palmas',
            'Granada CF': 'Granada',
            'UD Almería': 'Almeria',
            'FC Barcelona': 'Barcelona',

            # Bundesliga
            'Bayer 04 Leverkusen': 'Leverkusen',
            'FC Bayern München': 'Bayern Munich',
            'VfB Stuttgart': 'Stuttgart',
            'RB Leipzig': 'Leipzig',
            'Borussia Dortmund': 'Dortmund',
            'Eintracht Frankfurt': 'Frankfurt',
            'TSG 1899 Hoffenheim': 'Hoffenheim',
            '1. FC Heidenheim 1846': 'Heidenheim',
            'SV Werder Bremen': 'Werder Bremen',
            'SC Freiburg': 'Freiburg',
            'FC Augsburg': 'Augsburg',
            'VfL Wolfsburg': 'Wolfsburg',
            '1. FSV Mainz 05': 'Mainz',
            'Borussia Mönchengladbach': 'M Gladbach',
            '1. FC Union Berlin': 'Union Berlin',
            'VfL Bochum 1848': 'Bochum',
            '1. FC Köln': 'Koln',
            'SV Darmstadt 98': 'Darmstadt',
            'FC St. Pauli 1910': 'St Pauli',
            'Holstein Kiel': 'Holstein Kiel',
            
             # Serie A
            'FC Internazionale Milano': 'Inter',
            'AC Milan': 'Milan',
            'Juventus FC': 'Juventus',
            'Bologna FC 1909': 'Bologna',
            'AS Roma': 'Roma',
            'Atalanta BC': 'Atalanta',
            'SS Lazio': 'Lazio',
            'ACF Fiorentina': 'Fiorentina',
            'Torino FC': 'Torino',
            'SSC Napoli': 'Napoli',
            'Genoa CFC': 'Genoa',
            'AC Monza': 'Monza',
            'Hellas Verona FC': 'Verona',
            'US Lecce': 'Lecce',
            'Udinese Calcio': 'Udinese',
            'Cagliari Calcio': 'Cagliari',
            'Empoli FC': 'Empoli',
            'Frosinone Calcio': 'Frosinone',
            'US Sassuolo Calcio': 'Sassuolo',
            'US Salernitana 1919': 'Salernitana',
            'Parma Calcio 1913': 'Parma',
            'Como 1907': 'Como',
            'Venezia FC': 'Venezia',

            # Ligue 1
            'Paris Saint-Germain FC': 'PSG',
            'AS Monaco FC': 'Monaco',
            'Stade Brestois 29': 'Brest',
            'Lille OSC': 'Lille',
            'OGC Nice': 'Nice',
            'Olympique Lyonnais': 'Lyon',
            'Racing Club de Lens': 'Lens',
            'Olympique de Marseille': 'Marseille',
            'Stade de Reims': 'Reims',
            'Stade Rennais FC 1901': 'Rennes',
            'Toulouse FC': 'Toulouse',
            'Montpellier HSC': 'Montpellier',
            'RC Strasbourg Alsace': 'Strasbourg',
            'FC Nantes': 'Nantes',
            'Le Havre AC': 'Le Havre',
            'FC Metz': 'Metz',
            'FC Lorient': 'Lorient',
            'Clermont Foot 63': 'Clermont',
            'AS Saint-Étienne': 'St Etienne',
            'AJ Auxerre': 'Auxerre',
            'Angers SCO': 'Angers',

            # Brasileirão
            'SE Palmeiras': 'Palmeiras',
            'CR Flamengo': 'Flamengo',
            'Botafogo FR': 'Botafogo',
            'São Paulo FC': 'Sao Paulo',
            'Grêmio FBPA': 'Gremio',
            'Clube Atlético Mineiro': 'Atletico-MG',
            'Club Athletico Paranaense': 'Athletico-PR',
            'Fluminense FC': 'Fluminense',
            'Cuiabá EC': 'Cuiaba',
            'SC Corinthians Paulista': 'Corinthians',
            'Cruzeiro EC': 'Cruzeiro',
            'SC Internacional': 'Internacional',
            'Fortaleza EC': 'Fortaleza',
            'EC Bahia': 'Bahia',
            'CR Vasco da Gama': 'Vasco',
            'EC Juventude': 'Juventude',
            'AC Goianiense': 'Atletico-GO',
            'Criciúma EC': 'Criciuma',
            'EC Vitória': 'Vitoria',
            'Red Bull Bragantino': 'Bragantino',
            'Santos FC': 'Santos',
        }

        count_merged = 0

        for wrong_name, correct_name in name_mapping.items():
            wrong_teams = list(Team.objects.filter(name=wrong_name))
            if not wrong_teams:
                continue

            correct_team = Team.objects.filter(name=correct_name).first()

            if correct_team:
                target_team = correct_team
                source_teams = wrong_teams
                self.stdout.write(f"Mesclando '{wrong_name}' -> '{correct_name}'...")
            else:
                # Se o time correto não existe, promovemos o primeiro errado
                target_team = wrong_teams[0]
                source_teams = wrong_teams[1:]
                old_name = target_team.name
                target_team.name = correct_name
                try:
                    target_team.save()
                    self.stdout.write(f"Renomeando '{old_name}' -> '{correct_name}'...")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Erro ao renomear {old_name}: {e}"))
                    continue

            for source_team in source_teams:
                if source_team == target_team:
                    continue
                    
                # Move matches
                Match.objects.filter(home_team=source_team).update(home_team=target_team)
                Match.objects.filter(away_team=source_team).update(away_team=target_team)
                
                # Update API ID if target is empty
                if source_team.api_id and not target_team.api_id:
                    target_team.api_id = source_team.api_id
                    target_team.save()
                
                source_team.delete()
                count_merged += 1
                self.stdout.write(f"  > Time ID {source_team.id} mesclado/removido.")

        self.stdout.write(self.style.SUCCESS(f"Concluído! Total de times mesclados: {count_merged}"))
