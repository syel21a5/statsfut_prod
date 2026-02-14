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
                }
                
                mapped_league = league_map.get(raw_league_name)
                
                if not mapped_league:
                    continue  # Pula ligas desconhecidas
                
                # Busca ou cria liga (com tratamento de erro para duplicatas)
                try:
                    league_obj, _ = League.objects.get_or_create(
                        name=mapped_league['name'],
                        defaults={'country': mapped_league['country']}
                    )
                except League.MultipleObjectsReturned:
                    # Se houver múltiplas, pega a primeira (deveríamos limpar duplicatas depois)
                    league_obj = League.objects.filter(name=mapped_league['name']).first()
                    self.stdout.write(self.style.WARNING(f"Aviso: Múltiplas ligas encontradas para '{mapped_league['name']}'. Usando a primeira (ID: {league_obj.id})."))
                
                # Mapping names from Football-Data.org to local DB
                name_mapping = {
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
