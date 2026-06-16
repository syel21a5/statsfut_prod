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
    fetch_live_odds_api_england,
    fetch_live_odds_api_austria,
    fetch_live_odds_api_australia,
    fetch_upcoming_odds_api_australia
)
from matches.team_validation import is_team_valid_for_league
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
            self.stdout.write(self.style.SUCCESS('🔴 Buscando jogos AO VIVO (Ligas Habilitadas)...'))
            try:
                # RESTRITIVO: Busca apenas as ligas que o usuário habilitou expressamente
                enabled_leagues = [
                    {'name': 'Brasileirao', 'country': 'Brasil'},
                    {'name': 'Série B', 'country': 'Brasil'},
                    {'name': 'Série C', 'country': 'Brasil'},
                    {'name': 'La Liga', 'country': 'Espanha'},
                    {'name': 'Premier League', 'country': 'Inglaterra'},
                    {'name': 'Serie A', 'country': 'Italia'},
                    {'name': 'Primeira Liga', 'country': 'Portugal'},
                    {'name': 'Ligue 1', 'country': 'Franca'},
                    {'name': 'Bundesliga', 'country': 'Alemanha'},
                    {'name': 'Bundesliga', 'country': 'Austria'},
                    {'name': 'A-League', 'country': 'Australia'},
                    {'name': 'Pro League', 'country': 'Belgica'},
                    {'name': 'Super League', 'country': 'Suica'},
                    {'name': 'Eredivisie', 'country': 'Holanda'},
                    {'name': 'Super Lig', 'country': 'Turquia'},
                    {'name': 'Superliga', 'country': 'Dinamarca'},
                    {'name': 'Super League', 'country': 'Grecia'},
                    {'name': 'Liga Profesional', 'country': 'Argentina'},
                ]
                
                # Faz UMA ÚNICA chamada para a API com todos os jogos ao vivo do mundo
                all_live_fixtures = api_manager.get_live_fixtures()
                
                for lg in enabled_leagues:
                    try:
                        # Busca por league_ids mapeados no api_manager para essa liga
                        mapping = api_manager.LEAGUE_MAPPINGS.get(lg['name'])
                        if mapping:
                            # Filtra as partidas retornadas na única request
                            filtered_fixtures = [
                                f for f in all_live_fixtures 
                                if f.get('league_id') in mapping['api_football'] 
                                and (f.get('country') == lg['country'] or f.get('league') == lg['name'])
                            ]
                            
                            # SINCRONIZAÇÃO INTELIGENTE: Ligas do SofaScore permitem atualização de placar, mas com travas
                            is_sofascore_league = lg['name'] in ['Ligue 1', 'Bundesliga', 'Pro League', 'Super League', 'Premier League', 'Superliga', 'La Liga', 'Veikkausliiga']
                            
                            if filtered_fixtures:
                                self.stdout.write(f"  > Processando {len(filtered_fixtures)} jogos ao vivo para {lg['name']} ({lg['country']})")
                                # Passa a flag de proteção para o processador
                                self.process_fixtures(filtered_fixtures, is_live=True, readonly_structure=is_sofascore_league)
                            
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"  ⚠️ Erro ao processar liga {lg['name']}: {e}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro geral ao buscar jogos ao vivo: {e}'))

            try:
                from matches.services.live_radar import LiveRadarService
                self.stdout.write(self.style.SUCCESS('📸 Capturando snapshots para o Radar Ao Vivo...'))
                LiveRadarService.take_snapshots_for_active_matches()
                self.stdout.write(self.style.SUCCESS('✅ Snapshots capturados.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro ao capturar snapshots do Radar Ao Vivo: {e}'))
        
        if mode == 'upcoming' or mode == 'both':
            # The Odds API for Australia (Special Handling - Upcoming)
            self.stdout.write(self.style.SUCCESS('\n🔴 [SPECIAL] Buscando PRÓXIMOS JOGOS da A-League (Australia) via The Odds API...'))
            try:
                fetch_upcoming_odds_api_australia()
                self.stdout.write(self.style.SUCCESS('✅ Próximos jogos da A-League (Australia) atualizados via The Odds API.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro ao buscar jogos da A-League (Australia): {e}'))

            days_upcoming = 30
            if options.get('days') and options['days'] != 7: # Se usuário passou --days diferente do default, usa
                days_upcoming = options['days']
                
            self.stdout.write(self.style.SUCCESS(f'📅 Buscando próximos jogos ({days_upcoming} dias)...'))
            
            # Itera sobre cada liga mapeada para garantir uso correto das APIs
            for league_name in api_manager.LEAGUE_MAPPINGS.keys():
                # SINCRONIZAÇÃO INTELIGENTE: Pular criação de jogos, mas permitir atualização se o jogo já existir
                is_sofascore_league = league_name in ['Ligue 1', 'Austrian Bundesliga', 'A-League', 'Bundesliga', 'Pro League', 'Super League', 'Swiss Super League', 'Premier League', 'Superliga', 'La Liga', 'Veikkausliiga']
                
                self.stdout.write(f"  > Processando {league_name}...")
                try:
                    upcoming_fixtures = api_manager.get_upcoming_fixtures(league_name=league_name, days_ahead=days_upcoming)
                    if upcoming_fixtures:
                        self.process_fixtures(upcoming_fixtures, is_live=False, readonly_structure=is_sofascore_league)
                        self.stdout.write(self.style.SUCCESS(f'    ✅ {len(upcoming_fixtures)} jogos encontrados para {league_name}'))
                    else:
                        self.stdout.write(f"    Nenhum jogo encontrado para {league_name}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ❌ Erro ao buscar jogos de {league_name}: {e}'))

            # Países adicionais: APENAS se estiverem na lista seletiva
            # PROTEÇÃO SOFASCORE: Removida França, Áustria e Austrália pois são ingeridos 100% pelo SofaScore
            enabled_countries = []
            self.stdout.write(self.style.SUCCESS(f'\n🌍 Buscando próximos jogos por país (Ligas habilitadas, {days_upcoming} dias)...'))
            for country in enabled_countries:
                try:
                    fixtures = api_manager.get_upcoming_fixtures_by_country(country, days_ahead=days_upcoming)
                    if fixtures:
                        self.process_fixtures(fixtures, is_live=False)
                        self.stdout.write(self.style.SUCCESS(f'    ✅ {country}: {len(fixtures)} jogos'))
                    else:
                        self.stdout.write(f'    {country}: 0 jogos')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    {country}: {e}'))

        # --- MODO RECENT ---
        if mode in ['recent', 'both']:
            days_back = options.get('days', 7)
            self.stdout.write(self.style.SUCCESS(f'\n⏮️  Buscando resultados recentes (últimos {days_back} dias)...'))
            
            # Itera sobre cada liga mapeada
            # HOTFIX: Processa em lote para Football-Data.org (ela suporta várias ligas de uma vez, mas aqui estamos fazendo uma por uma)
            # Para otimizar, a função get_past_fixtures já sabe lidar com isso se passarmos league_name=None, 
            # MAS o loop abaixo força uma por uma.
            # Vamos manter o loop para garantir controle e log detalhado.
            
            for league_name in api_manager.LEAGUE_MAPPINGS.keys():
                # SINCRONIZAÇÃO INTELIGENTE: Pular criação de jogos, mas permitir atualização se o jogo já existir
                is_sofascore_league = league_name in ['Ligue 1', 'Austrian Bundesliga', 'A-League', 'Bundesliga', 'Pro League', 'Super League', 'Swiss Super League', 'Premier League', 'Superliga', 'La Liga', 'Veikkausliiga']
                
                self.stdout.write(f"  > Processando {league_name}...")
                try:
                    # Football-Data.org logic (implemented in api_manager)
                    past_fixtures = api_manager.get_past_fixtures(league_name=league_name, days_back=days_back)
                    if past_fixtures:
                        self.process_fixtures(past_fixtures, is_live=False, readonly_structure=is_sofascore_league)
                        self.stdout.write(self.style.SUCCESS(f'    ✅ {len(past_fixtures)} jogos processados para {league_name}'))
                    else:
                        self.stdout.write(f"    Nenhum jogo recente encontrado para {league_name}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ❌ Erro ao buscar jogos de {league_name}: {e}'))

    def _get_or_create_team(self, name, league, external_id, source_api='api_football'):
        # 1. Tenta buscar pelo id correto na mesma liga
        if external_id:
            if source_api == 'football_data':
                team = Team.objects.filter(fd_id=str(external_id), league=league).first()
            else:
                team = Team.objects.filter(api_id=str(external_id), league=league).first()
            
            if team:
                if team.name != name:
                    team.name = name
                    team.save()
                return team

        # 2. Se não achou pelo id na liga, busca por nome e liga
        try:
            team = Team.objects.get(name=name, league=league)
            if external_id:
                if source_api == 'football_data':
                    if not team.fd_id:
                        team.fd_id = str(external_id)
                        team.save()
                else:
                    if not team.api_id:
                        team.api_id = str(external_id)
                        team.save()
                    elif team.api_id != str(external_id):
                        if not Team.objects.filter(api_id=str(external_id)).exists():
                            team.api_id = str(external_id)
                            team.save()
            return team
        except Team.DoesNotExist:
            pass

        # 3. Se ainda não tem time, cria um novo
        try:
            create_api_id = None
            create_fd_id = None
            if external_id:
                if source_api == 'football_data':
                    create_fd_id = str(external_id)
                else:
                    if not Team.objects.filter(api_id=str(external_id)).exists():
                        create_api_id = str(external_id)
            return Team.objects.create(
                name=name,
                league=league,
                api_id=create_api_id,
                fd_id=create_fd_id
            )
        except Exception as e:
            if 'Duplicate entry' in str(e) or 'unique_team_name_per_league' in str(e):
                team = Team.objects.filter(name=name, league=league).first()
                if team:
                    return team
            raise e


    def _has_changes(self, match_obj, defaults):
        """Compara os dados da API com o objeto existente no banco.
        Retorna True se houver qualquer diferença que justifique um .save()."""
        for key, value in defaults.items():
            existing = getattr(match_obj, key, None)
            if existing != value:
                return True
        return False

    def process_fixtures(self, fixtures, is_live=False, readonly_structure=False):
        """Processa fixtures e salva/atualiza no banco. readonly_structure=True impede criação de novos jogos."""
        
        count_new = 0
        count_updated = 0
        count_skipped = 0
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
                    # Se não encontrou no mapa estático, tenta buscar direto do Banco de Dados
                    fx_country = fixture.get('country', '')
                    from matches.utils import COUNTRY_REVERSE_TRANSLATIONS
                    db_country = COUNTRY_REVERSE_TRANSLATIONS.get(fx_country.lower(), fx_country)
                    
                    league_obj = League.objects.filter(name__iexact=raw_league_name, country__iexact=db_country).first()
                    if league_obj:
                        mapped_league = {'name': league_obj.name, 'country': league_obj.country}
                    else:
                        continue  # Pula ligas desconhecidas que não estão no BD
                
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

                source_api = fixture.get('source_api', 'api_football')
                
                home_name = fixture['home_team']
                away_name = fixture['away_team']
                
                # CRITICAL: Validate teams BEFORE processing
                if not is_team_valid_for_league(home_name, league_obj.name):
                    self.stdout.write(self.style.WARNING(f'  🚫 Rejeitado: {home_name} não pertence à {league_obj.name} ({league_obj.country})'))
                    continue
                if not is_team_valid_for_league(away_name, league_obj.name):
                    self.stdout.write(self.style.WARNING(f'  🚫 Rejeitado: {away_name} não pertence à {league_obj.name} ({league_obj.country})'))
                    continue

                home_name = normalize_team_name(home_name)
                away_name = normalize_team_name(away_name)

                # Busca ou cria times usando o método seguro
                home_team = self._get_or_create_team(
                    home_name, 
                    league_obj, 
                    fixture.get('home_team_id'),
                    source_api
                )
                
                away_team = self._get_or_create_team(
                    away_name, 
                    league_obj, 
                    fixture.get('away_team_id'),
                    source_api
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
                    '1H': '1H',  # First Half
                    'HT': 'HT',  # Half Time
                    '2H': '2H',  # Second Half
                    'FT': 'FT',  # Full Time - PADRONIZADO com SofaScore
                    'AET': 'AET',  # After Extra Time
                    'PEN': 'PEN',  # Penalties
                    'PST': 'Postponed',
                    'CANC': 'Cancelled',
                    'ABD': 'Abandoned',
                    'SCHEDULED': 'Scheduled',
                    'IN_PLAY': 'LIVE',
                    'FINISHED': 'FT',  # PADRONIZADO: sempre usar FT
                }
                
                status = status_map.get(fixture['status'], 'Scheduled')
                
                # Dados para salvar
                match_external_id = str(fixture['id']) if fixture.get('id') else None
                
                defaults = {
                    'date': match_date,
                    'status': status,
                    'elapsed_time': fixture.get('elapsed'),
                }
                
                if source_api == 'football_data':
                    defaults['fd_id'] = match_external_id
                else:
                    defaults['api_id'] = match_external_id
                
                # PROTEÇÃO: Só atualiza scores se a API realmente trouxe dados
                # Evita sobrescrever scores válidos do SofaScore com None
                if fixture['home_score'] is not None:
                    defaults['home_score'] = fixture['home_score']
                if fixture['away_score'] is not None:
                    defaults['away_score'] = fixture['away_score']
                
                # Lógica segura para Match: Prioriza busca por api_id ou fd_id
                match_obj = None
                created = False
                if match_external_id:
                    try:
                        if source_api == 'football_data':
                            match_obj = Match.objects.get(fd_id=match_external_id)
                        else:
                            match_obj = Match.objects.get(api_id=match_external_id)
                            
                        # OTIMIZAÇÃO: Só salva se houver mudança real
                        if self._has_changes(match_obj, defaults) or match_obj.league_id != league_obj.id or match_obj.season_id != season_obj.id or match_obj.home_team_id != home_team.id or match_obj.away_team_id != away_team.id:
                            # Atualiza campos
                            for key, value in defaults.items():
                                setattr(match_obj, key, value)
                            # Atualiza relacionamentos
                            match_obj.league = league_obj
                            match_obj.season = season_obj
                            match_obj.home_team = home_team
                            match_obj.away_team = away_team
                            match_obj.save()
                        else:
                            # Nenhuma mudança detectada, pula o save
                            count_skipped += 1
                            continue
                    except Match.DoesNotExist:
                        pass
                
                if not match_obj:
                    # Se readonly_structure estiver ativo, NUNCA criamos jogos novos para evitar duplicatas do SofaScore
                    if readonly_structure:
                        self.stdout.write(self.style.WARNING(f'  ⚠️ Ignorado (Read-Only): {home_team.name} vs {away_team.name} não existe no banco.'))
                        continue

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
                    # OTIMIZAÇÃO: Só recalcula standings se o jogo mudou para status finalizado
                    if status in ['FT', 'Finished', 'AET', 'PEN']:
                        touched_leagues.add((league_obj.name, league_obj.country))
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Erro ao processar fixture: {e}'))
                continue
        
        self.stdout.write(f'📊 Resumo: {count_new} novos, {count_updated} atualizados, {count_skipped} sem alteração (poupados)')
        
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
