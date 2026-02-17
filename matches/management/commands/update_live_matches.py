from django.core.management.base import BaseCommand
from django.conf import settings
from matches.models import League, Team, Match, Season
from matches.api_manager import APIManager
from django.utils import timezone
from datetime import datetime
import pytz

class Command(BaseCommand):
    help = 'Atualiza jogos ao vivo e próximos jogos usando as APIs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='both',
            help='Modo: live (ao vivo), upcoming (próximos), ou both (ambos)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força execução mesmo em DEBUG'
        )

    def handle(self, *args, **options):
        if settings.DEBUG and not options['force']:
            self.stdout.write(self.style.ERROR("ERRO: Este comando consome API e não deve ser executado em ambiente de desenvolvimento (DEBUG=True). Use --force se realmente necessário."))
            return

        mode = options['mode']
        
        api_manager = APIManager()
        
        # Coleta IDs da API-Football de todas as ligas mapeadas
        all_api_football_ids = []
        for m in api_manager.LEAGUE_MAPPINGS.values():
            all_api_football_ids.extend(m['api_football'])
        
        if mode in ['live', 'both']:
            self.stdout.write(self.style.SUCCESS('🔴 Buscando jogos AO VIVO (Todas as Ligas)...'))
            try:
                # Se não passar league_ids, busca de todas as ligas configuradas/suportadas
                live_fixtures = api_manager.get_live_fixtures()
                self.process_fixtures(live_fixtures, is_live=True)
                self.stdout.write(self.style.SUCCESS(f'✅ {len(live_fixtures)} jogos ao vivo processados'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro ao buscar jogos ao vivo: {e}'))
        
        if mode in ['upcoming', 'both']:
            self.stdout.write(self.style.SUCCESS('📅 Buscando próximos jogos (15 dias)...'))
            
            # Itera sobre cada liga mapeada para garantir uso correto das APIs
            for league_name in api_manager.LEAGUE_MAPPINGS.keys():
                self.stdout.write(f"  > Processando {league_name}...")
                try:
                    upcoming_fixtures = api_manager.get_upcoming_fixtures(league_name=league_name, days_ahead=15)
                    if upcoming_fixtures:
                        self.process_fixtures(upcoming_fixtures, is_live=False)
                        self.stdout.write(self.style.SUCCESS(f'    ✅ {len(upcoming_fixtures)} jogos encontrados para {league_name}'))
                    else:
                        self.stdout.write(f"    Nenhum jogo encontrado para {league_name}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ❌ Erro ao buscar jogos de {league_name}: {e}'))

            # Países adicionais: tenta por país (principal liga) quando não há mapping
            countries = [
                'Argentina','Australia','Austria','Belgium','Brazil','Czech Republic','Denmark','England',
                'Finland','France','Germany','Greece','Italy','Japan','Netherlands','Norway','Poland',
                'Portugal','Russia','Sweden','Turkey','Ukraine','Switzerland'
            ]
            self.stdout.write(self.style.SUCCESS('\n🌍 Buscando próximos jogos por país (ligas principais)...'))
            for country in countries:
                try:
                    fixtures = api_manager.get_upcoming_fixtures_by_country(country, days_ahead=15)
                    if fixtures:
                        self.process_fixtures(fixtures, is_live=False)
                        self.stdout.write(self.style.SUCCESS(f'    ✅ {country}: {len(fixtures)} jogos'))
                    else:
                        self.stdout.write(f'    {country}: 0 jogos')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    {country}: {e}'))

    def _get_or_create_team(self, name, league, api_id):
        # 1. Tenta buscar pelo api_id se existir
        if api_id:
            try:
                return Team.objects.get(api_id=str(api_id))
            except Team.DoesNotExist:
                pass

        # 2. Se não achou pelo api_id, busca por nome e liga
        try:
            team = Team.objects.get(name=name, league=league)
            if api_id:
                # Se achou e tem api_id novo, atualiza (sabemos que api_id está livre pois passo 1 falhou)
                team.api_id = str(api_id)
                team.save()
            return team
        except Team.DoesNotExist:
            pass

        # 3. Se ainda não tem time, cria um novo
        try:
            return Team.objects.create(
                name=name,
                league=league,
                api_id=str(api_id) if api_id else None
            )
        except Exception as e:
            # Se der erro de duplicata, tenta buscar de novo pelo api_id (pode ter sido criado em paralelo ou inconsistência)
            if 'Duplicate entry' in str(e) and api_id:
                try:
                    return Team.objects.get(api_id=str(api_id))
                except Team.DoesNotExist:
                    pass
            raise e


    def process_fixtures(self, fixtures, is_live=False):
        """Processa fixtures e salva/atualiza no banco"""
        
        count_new = 0
        count_updated = 0
        
        for fixture in fixtures:
            try:
                raw_league_name = fixture['league']
                
                # Mapa robusto de nomes de ligas das APIs para o Banco
                league_map = {
                    'Premier League': {'name': 'Premier League', 'country': 'Inglaterra'},
                    'Primera Division': {'name': 'La Liga', 'country': 'Espanha'},
                    'La Liga': {'name': 'La Liga', 'country': 'Espanha'},
                    'Bundesliga': {'name': 'Bundesliga', 'country': 'Alemanha'},
                    'Serie A': {'name': 'Serie A', 'country': 'Italia'},
                    'Ligue 1': {'name': 'Ligue 1', 'country': 'Franca'},
                    'Campeonato Brasileiro Série A': {'name': 'Brasileirão', 'country': 'Brasil'},
                    'Brasileirão Série A': {'name': 'Brasileirão', 'country': 'Brasil'},
                    'Pro League': {'name': 'Pro League', 'country': 'Belgica'},
                    'Jupiler Pro League': {'name': 'Pro League', 'country': 'Belgica'},
                    'First Division A': {'name': 'Pro League', 'country': 'Belgica'},
                    # Extras mapeados por país
                    'Primeira Liga': {'name': 'Primeira Liga', 'country': 'Portugal'},
                    'Liga Portugal': {'name': 'Primeira Liga', 'country': 'Portugal'},
                    'Eredivisie': {'name': 'Eredivisie', 'country': 'Holanda'},
                    'Süper Lig': {'name': 'Super Lig', 'country': 'Turquia'},
                    'Super Lig': {'name': 'Super Lig', 'country': 'Turquia'},
                    'Superliga': {'name': 'Superliga', 'country': 'Dinamarca'},
                    'Superligaen': {'name': 'Superliga', 'country': 'Dinamarca'},
                    'Super League 1': {'name': 'Super League', 'country': 'Grecia'},
                    'Super League': {'name': 'Super League', 'country': 'Suica'},  # desambiguado abaixo
                    'Swiss Super League': {'name': 'Super League', 'country': 'Suica'},
                    'Austrian Bundesliga': {'name': 'Bundesliga', 'country': 'Austria'},
                    # Algumas APIs usam apenas "Bundesliga" para Áustria: desambiguado abaixo
                    'Allsvenskan': {'name': 'Allsvenskan', 'country': 'Suecia'},
                    'Eliteserien': {'name': 'Eliteserien', 'country': 'Noruega'},
                    'Veikkausliiga': {'name': 'Veikkausliiga', 'country': 'Finlandia'},
                    'Ekstraklasa': {'name': 'Ekstraklasa', 'country': 'Polonia'},
                    'J1 League': {'name': 'J1 League', 'country': 'Japao'},
                    'Meiji Yasuda J1 League': {'name': 'J1 League', 'country': 'Japao'},
                    'A-League': {'name': 'A-League', 'country': 'Australia'},
                    'A-League Men': {'name': 'A-League', 'country': 'Australia'},
                    'Czech Liga': {'name': 'First League', 'country': 'Republica Tcheca'},
                }
                
                mapped_league = league_map.get(raw_league_name)
                
                if not mapped_league:
                    continue  # Pula ligas desconhecidas
                
                # Preferir país da fixture quando disponível para desambiguar nomes (ex.: Bundesliga)
                fx_country = fixture.get('country')
                if fx_country:
                    from matches.utils import COUNTRY_REVERSE_TRANSLATIONS
                    db_country = COUNTRY_REVERSE_TRANSLATIONS.get(fx_country.lower(), fx_country)
                    if db_country:
                        mapped_league['country'] = db_country

                # Buscar por nome+país para evitar colisões
                league_obj = League.objects.filter(
                    name=mapped_league['name'],
                    country=mapped_league['country']
                ).first()
                if not league_obj:
                    league_obj = League.objects.create(
                        name=mapped_league['name'],
                        country=mapped_league['country']
                    )

                # Mapping names from Football-Data.org/API-Football to local DB
                name_mapping = {
                    # Premier League
                    'Manchester United FC': 'Manchester Utd',
                    'Manchester City FC': 'Manchester City',
                    'West Ham United FC': 'West Ham',
                    'Newcastle United FC': 'Newcastle',
                    'Tottenham Hotspur FC': 'Tottenham',
                    'Wolverhampton Wanderers FC': 'Wolves',
                    'Leicester City FC': 'Leicester',
                    'Leeds United FC': 'Leeds',
                    'Brighton & Hove Albion FC': 'Brighton',
                    'Arsenal FC': 'Arsenal',
                    'Chelsea FC': 'Chelsea',
                    'Liverpool FC': 'Liverpool',
                    'Everton FC': 'Everton',
                    'Fulham FC': 'Fulham',
                    'Brentford FC': 'Brentford',
                    'Crystal Palace FC': 'Crystal Palace',
                    'Southampton FC': 'Southampton',
                    'Aston Villa FC': 'Aston Villa',
                    'Sheffield United FC': 'Sheffield United',
                    'Burnley FC': 'Burnley',
                    'Luton Town FC': 'Luton',
                    'Norwich City FC': 'Norwich',
                    'Watford FC': 'Watford',
                    'Nottingham Forest FC': 'Nottingham',
                    'Ipswich Town FC': 'Ipswich',

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
                    'Santos FC': 'Santos', # Caso volte ou jogue copa

                    # Pro League (Bélgica)
                    'Union Saint-Gilloise': 'Royale Union SG',
                    'Union St.-Gilloise': 'Royale Union SG',
                    'Union St.Gilloise': 'Royale Union SG',
                    'St. Gilloise': 'Royale Union SG',
                    'St Gilloise': 'Royale Union SG',
                    'Sint-Truiden': 'Sint-Truiden',
                    'St Truiden': 'Sint-Truiden',
                    'St. Truiden': 'Sint-Truiden',
                    'KRC Genk': 'Genk',
                    'RSC Anderlecht': 'Anderlecht',
                    'KV Mechelen': 'Mechelen',
                    'Royal Antwerp FC': 'Antwerp',
                    'Sporting Charleroi': 'Charleroi',
                    'Standard Liège': 'Standard Liege',
                    'Oud-Heverlee Leuven': 'OH Leuven',
                    'RAAL La Louvière': 'La Louviere',
                    'RAAL La Louviere': 'La Louviere',
                    'Cercle Brugge KSV': 'Cercle Brugge',
                }
                
                home_name = fixture['home_team']
                away_name = fixture['away_team']
                
                home_name = name_mapping.get(home_name, home_name)
                away_name = name_mapping.get(away_name, away_name)

                # Busca ou cria times usando o método seguro
                home_team = self._get_or_create_team(
                    home_name, 
                    league_obj, 
                    fixture.get('home_team_id')
                )
                
                away_team = self._get_or_create_team(
                    away_name, 
                    league_obj, 
                    fixture.get('away_team_id')
                )
                
                # Parse data
                try:
                    match_date = datetime.fromisoformat(fixture['date'].replace('Z', '+00:00'))
                    if timezone.is_naive(match_date):
                        match_date = timezone.make_aware(match_date, pytz.UTC)
                except:
                    match_date = None
                
                # Determina temporada (ano de término)
                if match_date:
                    year = match_date.year
                    # Se for entre Jan-Jul, é temporada do ano atual
                    # Se for Ago-Dez, é temporada do ano seguinte
                    if match_date.month >= 8:
                        season_year = year + 1
                    else:
                        season_year = year
                else:
                    season_year = datetime.now().year
                
                season_obj, _ = Season.objects.get_or_create(year=season_year)
                
                # Determina status
                status_map = {
                    'NS': 'Scheduled',  # Not Started
                    'LIVE': 'Live',
                    '1H': 'Live',  # First Half
                    'HT': 'Live',  # Half Time
                    '2H': 'Live',  # Second Half
                    'FT': 'Finished',  # Full Time
                    'AET': 'Finished',  # After Extra Time
                    'PEN': 'Finished',  # Penalties
                    'PST': 'Postponed',
                    'CANC': 'Cancelled',
                    'ABD': 'Abandoned',
                    'SCHEDULED': 'Scheduled',
                    'IN_PLAY': 'Live',
                    'FINISHED': 'Finished',
                }
                
                status = status_map.get(fixture['status'], 'Scheduled')
                
                # Dados para salvar
                match_api_id = str(fixture['id']) if fixture.get('id') else None
                
                defaults = {
                    'date': match_date,
                    'status': status,
                    'home_score': fixture['home_score'],
                    'away_score': fixture['away_score'],
                    'elapsed_time': fixture.get('elapsed'),
                    'api_id': match_api_id
                }
                
                # Lógica segura para Match: Prioriza busca por api_id
                match_obj = None
                created = False
                if match_api_id:
                    try:
                        match_obj = Match.objects.get(api_id=match_api_id)
                        # Atualiza campos
                        for key, value in defaults.items():
                            setattr(match_obj, key, value)
                        # Atualiza relacionamentos
                        match_obj.league = league_obj
                        match_obj.season = season_obj
                        match_obj.home_team = home_team
                        match_obj.away_team = away_team
                        match_obj.save()
                    except Match.DoesNotExist:
                        pass
                
                if not match_obj:
                    # Se não achou por ID, tenta por chaves naturais (mas cuidado com api_id duplicado no defaults)
                    # Se formos criar, precisamos garantir que o api_id não colida (o que não deve acontecer se o passo acima falhou)
                    match_obj, created = Match.objects.update_or_create(
                        league=league_obj,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        defaults=defaults
                    )
                

                
                if created:
                    count_new += 1
                    self.stdout.write(f'  ➕ Novo: {home_team.name} vs {away_team.name}')
                else:
                    count_updated += 1
                    if is_live:
                        self.stdout.write(f'  🔄 Atualizado: {home_team.name} {fixture["home_score"]}-{fixture["away_score"]} {away_team.name} ({fixture.get("elapsed", "?")}\')')
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Erro ao processar fixture: {e}'))
                continue
        
        self.stdout.write(f'📊 Resumo: {count_new} novos, {count_updated} atualizados')
