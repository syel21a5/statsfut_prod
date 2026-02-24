from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from matches.models import League, Team, Match, Season
from matches.api_manager import APIManager
from matches.utils import normalize_team_name
from matches.utils_odds_api import (
    fetch_live_odds_api_argentina, 
    fetch_upcoming_odds_api_argentina,
    fetch_live_odds_api_brazil,
    fetch_live_odds_api_england
)
from django.utils import timezone
from datetime import datetime, timedelta
import pytz

class Command(BaseCommand):
    help = 'Atualiza jogos ao vivo e próximos jogos usando as APIs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='both',
            help='Modo: live (ao vivo), upcoming (próximos), recent (recentes), ou both (ambos live+upcoming)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Número de dias para buscar (usado em upcoming/recent) [Padrão: 7 para recent, 30 para upcoming]'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força execução mesmo em DEBUG=True'
        )

    def should_check_live_league(self, league_name, country):
        """
        Verifica se há jogos de uma liga hoje (ou em andamento) que justifiquem chamar a API ao vivo.
        Retorna True se houver jogo 'Live' ou agendado para começar em breve (< 45 min) ou hoje ainda não finalizado.
        """
        # 1. Encontrar a Liga
        league = League.objects.filter(name__icontains=league_name, country=country).first()
        if not league:
            return False 

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999)

        # 2. Buscar jogos de hoje que NÃO estão finalizados
        matches_today = Match.objects.filter(
            league=league,
            date__range=(today_start, today_end)
        ).exclude(status__in=['Finished', 'FT', 'AET', 'PEN', 'FINISHED'])
        
        # Se não tem jogo hoje não finalizado, verifica se tem algum jogo "Live" perdido de ontem
        if not matches_today.exists():
            live_matches = Match.objects.filter(
                league=league,
                status__in=['Live', '1H', '2H', 'HT', 'ET', 'P', 'In Play']
            )
            if live_matches.exists():
                return True
            
            # Se chegou aqui, não tem nada relevante
            self.stdout.write(self.style.WARNING(f"⚠️  [Smart Check] Nenhum jogo da {league_name} agendado para hoje ou em andamento. Pulando API."))
            return False

        # 3. Se tem jogos hoje, verificar horário
        # Verifica se algum jogo já começou (date <= now) OU vai começar em breve (date <= now + 45min)
        threshold = now + timedelta(minutes=45)
        
        # Jogos ativos = Jogos que já deveriam ter começado (incluindo atrasados/live) OU começam em < 45 min
        active_matches = matches_today.filter(date__lte=threshold)
        
        if active_matches.exists():
            return True
        else:
            # Tem jogo hoje, mas ainda falta muito tempo
            next_match = matches_today.filter(date__gt=now).order_by('date').first()
            if next_match:
                wait_min = int((next_match.date - now).total_seconds() / 60)
                self.stdout.write(self.style.WARNING(f"⚠️  [Smart Check] Próximo jogo da {league_name} em {wait_min} min ({next_match.date.strftime('%H:%M')}). Pulando API por enquanto."))
            return False

    def handle(self, *args, **options):
        # Hotfix: Ensure DEBUG doesn't block if force is used
        if settings.DEBUG and not options['force']:
            self.stdout.write(self.style.ERROR("ERRO: Este comando consome API e não deve ser executado em ambiente de desenvolvimento (DEBUG=True). Use --force se realmente necessário."))
            return

        mode = options['mode']
        # days = options['days'] # Removed this line as it was causing UnboundLocalError or unused var warning if not careful, accessing via options.get later
        
        api_manager = APIManager()
        
        if mode == 'live' or mode == 'both':
            pass # A lógica de Live foi movida para o início do handle() para usar o Smart Check antes de tudo.
            # O código acima já chamou as APIs se necessário.
            
        if mode == 'upcoming' or mode == 'both':
            fetch_upcoming_odds_api_argentina()
            # Futuramente: fetch_upcoming_odds_api_brazil()
            # Futuramente: fetch_upcoming_odds_api_england()
        all_api_football_ids = []
        for m in api_manager.LEAGUE_MAPPINGS.values():
            all_api_football_ids.extend(m['api_football'])
        
        if mode in ['live', 'both']:
            # The Odds API for Argentina (Special Handling) - Run first to ensure it runs
            self.stdout.write(self.style.SUCCESS('\n🔴 [SPECIAL] Verificando necessidade de buscar jogos AO VIVO da Liga Profesional (Argentina)...'))
            
            if self.should_check_live_argentina():
                self.stdout.write(self.style.SUCCESS('⚡ Jogo detectado ou iminente! Chamando The Odds API...'))
                try:
                    fetch_live_odds_api_argentina()
                    self.stdout.write(self.style.SUCCESS('✅ Jogos da Liga Profesional atualizados via The Odds API.'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Erro ao buscar jogos da Liga Profesional: {e}'))
            else:
                self.stdout.write(self.style.SUCCESS('💤 Modo economia: API não chamada.'))

            self.stdout.write(self.style.SUCCESS('🔴 Buscando jogos AO VIVO (Todas as Ligas)...'))
            try:
                # Se não passar league_ids, busca de todas as ligas configuradas/suportadas
                live_fixtures = api_manager.get_live_fixtures()
                self.process_fixtures(live_fixtures, is_live=True)
                self.stdout.write(self.style.SUCCESS(f'✅ {len(live_fixtures)} jogos ao vivo processados'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro ao buscar jogos ao vivo: {e}'))

        
        if mode in ['upcoming', 'both']:
            # The Odds API for Argentina (Special Handling)
            self.stdout.write(self.style.SUCCESS('\n🔴 [SPECIAL] Buscando PRÓXIMOS JOGOS da Liga Profesional (Argentina) via The Odds API...'))
            try:
                fetch_upcoming_odds_api_argentina()
                self.stdout.write(self.style.SUCCESS('✅ Próximos jogos da Liga Profesional atualizados via The Odds API.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro ao buscar jogos da Liga Profesional: {e}'))

            days_upcoming = 30
            if options.get('days') and options['days'] != 7: # Se usuário passou --days diferente do default, usa
                days_upcoming = options['days']
                
            self.stdout.write(self.style.SUCCESS(f'📅 Buscando próximos jogos ({days_upcoming} dias)...'))
            
            # Itera sobre cada liga mapeada para garantir uso correto das APIs
            for league_name in api_manager.LEAGUE_MAPPINGS.keys():
                self.stdout.write(f"  > Processando {league_name}...")
                try:
                    upcoming_fixtures = api_manager.get_upcoming_fixtures(league_name=league_name, days_ahead=days_upcoming)
                    if upcoming_fixtures:
                        self.process_fixtures(upcoming_fixtures, is_live=False)
                        self.stdout.write(self.style.SUCCESS(f'    ✅ {len(upcoming_fixtures)} jogos encontrados para {league_name}'))
                    else:
                        self.stdout.write(f"    Nenhum jogo encontrado para {league_name}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ❌ Erro ao buscar jogos de {league_name}: {e}'))

            # Países adicionais: tenta por país (principal liga) quando não há mapping
            # Removidos países já cobertos por LEAGUE_MAPPINGS para evitar duplicidade de chamadas
            countries = [
                'Australia','Austria','Czech Republic','Finland','Greece','Japan','Norway','Poland',
                'Russia','Sweden','Ukraine','Switzerland'
            ]
            self.stdout.write(self.style.SUCCESS(f'\n🌍 Buscando próximos jogos por país (ligas principais, {days_upcoming} dias)...'))
            for country in countries:
                try:
                    fixtures = api_manager.get_upcoming_fixtures_by_country(country, days_ahead=days_upcoming)
                    if fixtures:
                        self.process_fixtures(fixtures, is_live=False)
                        self.stdout.write(self.style.SUCCESS(f'    ✅ {country}: {len(fixtures)} jogos'))
                    else:
                        self.stdout.write(f'    {country}: 0 jogos')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    {country}: {e}'))

        if mode in ['recent', 'both']:
            days_back = options.get('days', 7)
            self.stdout.write(self.style.SUCCESS(f'\n⏮️  Buscando resultados recentes (últimos {days_back} dias)...'))
            
            # Itera sobre cada liga mapeada
            for league_name in api_manager.LEAGUE_MAPPINGS.keys():
                self.stdout.write(f"  > Processando {league_name}...")
                try:
                    # Football-Data.org logic (implemented in api_manager)
                    past_fixtures = api_manager.get_past_fixtures(league_name=league_name, days_back=days_back)
                    if past_fixtures:
                        self.process_fixtures(past_fixtures, is_live=False)
                        self.stdout.write(self.style.SUCCESS(f'    ✅ {len(past_fixtures)} jogos processados para {league_name}'))
                    else:
                        self.stdout.write(f"    Nenhum jogo recente encontrado para {league_name}")
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
        touched_leagues = set()
        
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
                    'Campeonato Brasileiro Série A': {'name': 'Brasileirao', 'country': 'Brasil'},
                    'Brasileirão Série A': {'name': 'Brasileirao', 'country': 'Brasil'},
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
                    'Liga Profesional': {'name': 'Liga Profesional', 'country': 'Argentina'},
                    'Liga Profesional de Fútbol': {'name': 'Liga Profesional', 'country': 'Argentina'},
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
                
                # Marcar liga tocada para recalcular tabela depois
                touched_leagues.add((league_obj.name, league_obj.country))

                # Mapping names from Football-Data.org/API-Football to local DB

                
                home_name = fixture['home_team']
                away_name = fixture['away_team']
                
                home_name = normalize_team_name(home_name)
                away_name = normalize_team_name(away_name)

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
                    touched_leagues.add((league_obj.name, league_obj.country))
                else:
                    count_updated += 1
                    if is_live:
                        self.stdout.write(f'  🔄 Atualizado: {home_team.name} {fixture["home_score"]}-{fixture["away_score"]} {away_team.name} ({fixture.get("elapsed", "?")}\')')
                    touched_leagues.add((league_obj.name, league_obj.country))
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Erro ao processar fixture: {e}'))
                continue
        
        self.stdout.write(f'📊 Resumo: {count_new} novos, {count_updated} atualizados')
        
        # Recalcular standings automaticamente para ligas afetadas
        if touched_leagues:
            try:
                from django.core.management import call_command
                for lg_name, lg_country in sorted(touched_leagues):
                    try:
                        self.stdout.write(self.style.SUCCESS(f'🧮 Recalculando standings: {lg_name} ({lg_country})'))
                        call_command('recalculate_standings', league_name=lg_name, country=lg_country)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  ⚠️ Falha ao recalcular {lg_name} ({lg_country}): {e}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️ Não foi possível invocar recalculate_standings: {e}'))
