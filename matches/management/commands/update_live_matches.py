from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from django.db import IntegrityError
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
import random
import time
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
                # TODAS as ligas monitoradas no banco (via SOFA_LEAGUE_IDS). Qualquer jogo
                # ao vivo nessas ligas é processado — se tiver 10 jogos ao vivo, mostra 10.
                from matches.services.sofascore_tor import SOFA_LEAGUE_IDS as _SOFA_IDS
                enabled_leagues = [{'name': k, 'country': ''} for k in _SOFA_IDS.keys()]
                # Preenche o país de cada liga (usado no filtro abaixo)
                _country_map = {
                    'Brasileirão': 'Brasil', 'Série B': 'Brasil', 'Série C': 'Brasil',
                    'Copa do Brasil': 'Brasil', 'La Liga': 'Espanha', 'Premier League': 'Inglaterra',
                    'Serie A': 'Italia', 'Primeira Liga': 'Portugal', 'Ligue 1': 'Franca',
                    'Bundesliga': 'Alemanha', 'A-League Men': 'Australia', 'Pro League': 'Belgica',
                    'Super League': 'Suica', 'Eredivisie': 'Holanda', 'Süper Lig': 'Turquia',
                    'Superliga': 'Dinamarca', 'Liga Profesional': 'Argentina', 'Primera B': 'Argentina',
                    'Liga Pro': 'Equador', 'Serie B (Equador)': 'Equador', 'Championship': 'Inglaterra',
                    'Premiership': 'Escocia', 'J1 League': 'Japao', 'Liga MX': 'Mexico',
                    'Ekstraklasa': 'Polonia', 'Veikkausliiga': 'Finlandia', 'Ykkösliiga': 'Finlandia',
                    'Besta deild karla': 'Islandia', '1. deild': 'Islandia', '1st Division': 'Noruega',
                    'Eliteserien': 'Noruega', 'Allsvenskan': 'Suecia', 'Superettan': 'Suecia',
                    'First League': 'Republica Tcheca', 'Premier Liga': 'Russia',
                    'Primera A': 'Colombia', 'Primera Division': 'Chile', 'Liga 1': 'Peru',
                    'MLS': 'Estados Unidos', 'USL Championship': 'Estados Unidos',
                    'Copa Libertadores': 'America do Sul', 'Copa Sul-Americana': 'America do Sul',
                    'Primeira Liga (PT)': 'Portugal',
                }
                for _lg in enabled_leagues:
                    if not _lg['country']:
                        _lg['country'] = _country_map.get(_lg['name'], '')
                
                # Faz UMA ÚNICA chamada para a API com todos os jogos ao vivo do mundo
                all_live_fixtures = api_manager.get_live_fixtures()
                
                # Filtra por ID DE TORNEIO (não por nome!) — o SofaScore muda nomes
                # (ex: "Copa Betano do Brasil" vs chave "Copa do Brasil"), mas os IDs
                # de torneio são estáveis. Qualquer jogo ao vivo de liga monitorada passa.
                from matches.services.sofascore_tor import SOFA_LEAGUE_IDS as SOFA_IDS
                _all_sofa_ids = set()
                for _v in SOFA_IDS.values():
                    _all_sofa_ids.update(_v)
                
                # Liga -> nome de liga canônico no banco (para o process_fixtures)
                _sofa_league_name = {}
                for _k, _v in SOFA_IDS.items():
                    for _tid in _v:
                        _sofa_league_name[_tid] = _k
                
                filtered_fixtures = [
                    f for f in all_live_fixtures
                    if f.get('source_api') == 'sofascore' and f.get('league_id') in _all_sofa_ids
                ]
                
                if filtered_fixtures:
                    self.stdout.write(self.style.SUCCESS(f"  ⚡ {len(filtered_fixtures)} jogos AO VIVO nas ligas monitoradas"))
                    # Liga habilitada p/ rich data (é SofaScore → readonly_structure p/ não criar duplicatas)
                    enabled_names = {_sofa_league_name.get(f.get('league_id'), f.get('league')) for f in filtered_fixtures}
                    self.process_fixtures(filtered_fixtures, is_live=True, readonly_structure=True)
                    # Rich data (chutes/escanteios/posse) roda no bloco abaixo para cada jogo live

                # ======================================================================
                # FALLBACK INDIVIDUAL (29/08/2026): o feed global do SofaScore
                # (/sport/football/events/live) é instável e às vezes NÃO inclui jogos
                # de certas ligas (ex: Série C brasileira). Para não deixar o placar
                # congelado, busca INDIVIDUALMENTE (via api_id) qualquer jogo que está
                # marcado como ao vivo no banco mas não apareceu no feed global.
                # ======================================================================
                try:
                    from matches.models import Match as _M
                    from matches.services.sofascore_tor import SofaScoreTorService as _SofaSvc
                    live_db_ids = {str(f.get('id')) for f in all_live_fixtures if f.get('id')}
                    _live_qs = _M.objects.filter(
                        status__in=['LIVE', 'Live', '1H', '2H', 'HT', 'ET', 'Halftime'],
                        api_id__isnull=False,
                        date__lte=timezone.now(),
                    ).exclude(api_id='')
                    _svc_fb = _SofaSvc()
                    _extra_fixtures = []
                    for _m2 in _live_qs:
                        _aid = str(_m2.api_id).replace('sofa_', '')
                        if not _aid.isdigit():
                            continue
                        if _aid in live_db_ids:
                            continue  # já veio no feed global
                        try:
                            _evdata = _svc_fb._fetch(f"https://www.sofascore.com/api/v1/event/{_aid}")
                            if not _evdata:
                                continue
                            _ev = _evdata.get('event') or {}
                            _st = (_ev.get('status') or {}).get('type')
                            if str(_st or '').lower() in ('finished', 'postponed', 'cancelled', 'abandoned'):
                                # saiu do radar: o bloco de stale marca FT em seguida
                                continue
                            _extra = _svc_fb._normalize(_ev)
                            _extra['source_api'] = 'sofascore'
                            _extra_fixtures.append(_extra)
                        except Exception as _e:
                            self.stdout.write(self.style.WARNING(f'  ⚠️ fallback individual {_aid} falhou: {_e}'))
                    if _extra_fixtures:
                        self.stdout.write(self.style.SUCCESS(f"  🔧 Fallback individual: {len(_extra_fixtures)} jogos ao vivo recuperados"))
                        self.process_fixtures(_extra_fixtures, is_live=True, readonly_structure=True)
                except Exception as _e2:
                    self.stdout.write(self.style.WARNING(f'  ⚠️ Erro no fallback individual: {_e2}'))

                else:
                    self.stdout.write('  (nenhum jogo ao vivo das ligas monitoradas agora)')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro geral ao buscar jogos ao vivo: {e}'))

            # AMBIENTE DE TESTE: marca FT jogos Live que saíram do radar do SofaScore
            # (o live global só lista jogos em andamento; quando o jogo termina, some da lista)
            try:
                from matches.services.sofascore_tor import SOFA_LEAGUE_IDS as _SOFA_IDS
                live_ids = {str(f.get('id')) for f in all_live_fixtures if f.get('id')}
                # Qualquer jogo Live que começou há >2h e não está mais no radar do SofaScore terminou
                stale = Match.objects.filter(
                    status__in=['LIVE', 'Live', '1H', '2H', 'HT', 'ET', 'Halftime'],
                    date__lte=timezone.now(),
                )
                marcados = 0
                for m in stale:
                    if m.api_id and str(m.api_id) in live_ids:
                        continue
                    if m.date and (timezone.now() - m.date).total_seconds() > 2 * 3600:
                        m.status = 'FT'
                        m.save()
                        marcados += 1
                if marcados:
                    self.stdout.write(self.style.SUCCESS(f'🏁 Marcados FT (sairam do live): {marcados}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Erro ao marcar FT stale: {e}'))

            # AMBIENTE DE TESTE: dados ricos do SofaScore (chutes, escanteios, posse, pressão)
            # para alimentar o Live Radar — via Tor
            try:
                from matches.services.sofascore_tor import SofaScoreTorService as _SofaSvc
                from matches.models import LiveMatchSnapshot as _Snapshot
                svc_rich = _SofaSvc()
                live_qs = Match.objects.filter(
                    status__in=['Live', 'LIVE', '1H', '2H', 'HT', 'ET', 'Halftime'],
                    date__lte=timezone.now(),
                )  # SEM LIMITE: rich data (chutes/escanteios/posse) para TODOS os jogos ao vivo
                for m in live_qs:
                    eid = None
                    if m.api_id and not str(m.api_id).startswith('sofa_'):
                        try:
                            eid = int(str(m.api_id))
                        except ValueError:
                            eid = None
                    if not eid:
                        continue
                    rich = svc_rich.get_match_rich_data(eid)
                    if not rich:
                        continue
                    m.home_shots = rich['home_shots']
                    m.away_shots = rich['away_shots']
                    m.home_shots_on_target = rich['home_shots_on_target']
                    m.away_shots_on_target = rich['away_shots_on_target']
                    m.home_shots_off_target = rich['home_shots_off_target']
                    m.away_shots_off_target = rich['away_shots_off_target']
                    m.home_corners = rich['home_corners']
                    m.away_corners = rich['away_corners']
                    m.home_possession = rich['home_possession']
                    m.away_possession = rich['away_possession']
                    m.home_fouls = rich['home_fouls']
                    m.away_fouls = rich['away_fouls']
                    m.home_dangerous_attacks = rich.get('home_dangerous_attacks')
                    m.away_dangerous_attacks = rich.get('away_dangerous_attacks')
                    m.home_big_chances = rich.get('home_big_chances')
                    m.away_big_chances = rich.get('away_big_chances')
                    m.statistics_data = {'graph_points': rich['graph_points'], 'source': 'sofascore_tor'}
                    m.save()
                    # Snapshot para o calculate_pressure clássico (por diferença)
                    _Snapshot.objects.create(
                        match=m,
                        minute=m.elapsed_time or 0,
                        home_shots_on_target=rich['home_shots_on_target'],
                        away_shots_on_target=rich['away_shots_on_target'],
                        home_shots_off_target=rich['home_shots_off_target'],
                        away_shots_off_target=rich['away_shots_off_target'],
                        home_corners=rich['home_corners'],
                        away_corners=rich['away_corners'],
                        home_possession=rich['home_possession'],
                        away_possession=rich['away_possession'],
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"📡 Radar: {m.home_team.name} x {m.away_team.name} | escanteios {rich['home_corners']}x{rich['away_corners']} | chutes {rich['home_shots']}x{rich['away_shots']} | posse {rich['home_possession']}x{rich['away_possession']}"
                    ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Erro rich data SofaScore: {e}'))

            # SANEAMENTO: jogos Scheduled que já passaram do horário e saíram do radar
            # (começaram/terminaram entre ciclos do loop) ficariam sem resultado para sempre.
            # Busca o status real de cada um no SofaScore (1 request/jogo via Tor) e grava o
            # resultado se acabou (FT), mantém se ainda não começou (adiado) etc.
            try:
                from matches.services.sofascore_tor import SofaScoreTorService as _SofaSvcSan
                svc_san = _SofaSvcSan()
                # Prioriza jogos com ID do SofaScore (8+ dígitos) — são os alimentados pelo Tor.
                # IDs antigos da API-Football (7 dígitos) dão 404 no SofaScore e são ignorados.
                sane_qs = Match.objects.filter(
                    status__in=['Scheduled', 'NS', 'SCHEDULED'],
                    date__lte=timezone.now() - timedelta(minutes=120),
                    api_id__isnull=False,
                ).exclude(api_id__startswith='ignored_')
                # Processa mais jogos por ciclo (era [:10]) e inclui TODOS os IDs numéricos,
                # inclusive os de 7 dígitos (API-Football) — o get_event_result tolera 404.
                sane_list = [m for m in sane_qs if str(m.api_id).lstrip('-').isdigit()][:25]
                # FALLBACK DETERMINÍSTICO: qualquer Scheduled cujo kickoff já passou há muito
                # tempo (>3h, jogo de futebol dura ~2h) SEM resultado na fonte é marcado FT —
                # evita jogo "upcoming" eterno e dispensa depender do Tor p/ sanear IDs antigos.
                hard_stale = Match.objects.filter(
                    status__in=['Scheduled', 'NS', 'SCHEDULED'],
                    date__lte=timezone.now() - timedelta(hours=3),
                ).exclude(api_id__startswith='ignored_')
                for ms in hard_stale[:30]:
                    if int((timezone.now() - ms.date).total_seconds() // 3600) > 3:
                        ms.status = 'FT'
                        ms.save()
                        self.stdout.write(self.style.SUCCESS(f'  🏁 FT (falback): {ms.home_team} x {ms.away_team}'))
                sane_fix = 0
                for m in sane_list:
                    try:
                        eid = int(str(m.api_id))
                    except (ValueError, TypeError):
                        continue
                    res = svc_san.get_event_result(eid)
                    if not res:
                        continue
                    if res['status'] == 'FT':
                        m.status = 'FT'
                        if res['home_score'] is not None:
                            m.home_score = res['home_score']
                        if res['away_score'] is not None:
                            m.away_score = res['away_score']
                        m.save()
                        sane_fix += 1
                        self.stdout.write(self.style.SUCCESS(f'  🏁 Saneado FT: {m.home_team} {m.home_score}-{m.away_score} {m.away_team}'))
                    elif res['status'] in ('PST', 'CANC', 'ABD', 'TBD'):
                        m.status = {'PST': 'Postponed', 'CANC': 'Cancelled', 'ABD': 'Abandoned', 'TBD': 'Postponed'}[res['status']]
                        m.save()
                        sane_fix += 1
                        self.stdout.write(self.style.SUCCESS(f'  🏁 Saneado {res["status"]}: {m.home_team} x {m.away_team}'))
                    time.sleep(random.uniform(0.3, 0.6))
                if sane_fix:
                    self.stdout.write(self.style.SUCCESS(f'  🧹 Saneamento: {sane_fix} jogos corrigidos'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Erro saneamento SofaScore: {e}'))

            try:
                from matches.services.live_radar import LiveRadarService
                self.stdout.write(self.style.SUCCESS('📸 Capturando snapshots para o Radar Ao Vivo...'))
                LiveRadarService.take_snapshots_for_active_matches()
                self.stdout.write(self.style.SUCCESS('✅ Snapshots capturados.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro ao capturar snapshots do Radar Ao Vivo: {e}'))

        # PREVENÇÃO DUPLICATAS: remove duplicatas criadas por fontes distintas (ex: SofaScore
        # vs API-Football) que inserem o mesmo jogo com nomes de times levemente diferentes,
        # mantendo o registro da fonte mais completa (api_id SofaScore atual).
        try:
            self._dedupe_matches()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠️ Erro dedupe: {e}'))
        
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
                # OTIMIZAÇÃO: NUNCA sobrescrever o nome do time no banco de dados com o nome da API.
                # Isso preserva os nomes canônicos limpos (ex: "Atletico-GO", "Sport Recife")
                # e evita que a API reescreva como "AC Goianiense" ou "Sport Club do Recife".
                return team

        # 2. Se não achou pelo id na liga, busca por nome e liga
        try:
            team = Team.objects.get(name=name, league=league)
            if external_id:
                if source_api == 'football_data':
                    if not team.fd_id:
                        # PROTEÇÃO: fd_id é unique GLOBAL (não por liga). O mesmo clube pode
                        # existir em várias ligas. Se outro time já usa esse fd_id, NÃO seta
                        # aqui — deixa None. Evita 'Duplicate entry' no live loop.
                        if not Team.objects.filter(fd_id=str(external_id)).exists():
                            team.fd_id = str(external_id)
                            team.save()
                    elif team.fd_id != str(external_id):
                        if not Team.objects.filter(fd_id=str(external_id)).exists():
                            team.fd_id = str(external_id)
                            team.save()
                else:
                    if not team.api_id:
                        # PROTEÇÃO: api_id é unique GLOBAL (não por liga). O mesmo clube pode
                        # existir em várias ligas (ex: Juventude na Série B e na Copa do Brasil).
                        # Se outro time já usa esse api_id, NÃO seta aqui — deixa None e o
                        # logo_url faz fallback por nome. Evita 'Duplicate entry' no live loop.
                        if not Team.objects.filter(api_id=str(external_id)).exists():
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


    def _dedupe_matches(self, lookahead_days=10):
        """Remove duplicatas de partidas na janela futura: mesmo par de times (normalizado)
        + mesma data, com mais de um registro. Mantém o registro mais completo (api_id com
        8+ dígitos / com score) e apaga os demais. Só mexe em Scheduled/NS; nunca em Live."""
        import re
        from collections import defaultdict
        from django.utils import timezone as _tz
        from datetime import timedelta as _td

        def _norm_club(name):
            import unicodedata as _uni
            s = str(name).lower()
            # remove acentos/acentuação
            s = _uni.normalize('NFD', s)
            s = ''.join(c for c in s if not _uni.combining(c))
            s = re.sub(r'\b(club atletico|club deportivo|club|c\.a\.|ca |fc |f\.c\.|ac |a\.c\.|de |del |da |do |dos |das |s\.a\.|sad|ltda|old boys|de cordoba|de santa fe|de santiago)\b', '', s)
            # colapsa grafias argentinas (dentro da mesma liga; acentos já removidos)
            s = re.sub(r'\bnewell.?s\b', 'newells', s)
            s = re.sub(r'\bjuniors?\b|\bjrs?\b', 'juniors', s)
            s = re.sub(r'\bgimnasia\b[ .]?l\.?p\.?|\bgimnasia y esgrima\b', 'gimnasia', s)
            s = re.sub(r'\btalleres\b.*\bcordoba\b|\bca talleres\b', 'talleres', s)
            s = re.sub(r'\bca lanus\b|\bclub atletico lanus\b', 'lanus', s)
            s = re.sub(r'\bestudiantes\b[ .]?l\.?p\.?|\bestudiantes( | de | de la | la )plata', 'estudiantes', s)
            s = re.sub(r'\bcentral cordoba( santiago)?\b', 'central cordoba', s)
            return ' '.join(s.split())

        now = _tz.now()
        qs = Match.objects.filter(
            date__gte=now,
            date__lte=now + _td(days=lookahead_days),
        ).select_related('home_team', 'away_team')
        groups = defaultdict(list)
        for m in qs:
            key = (m.date.date(), m.league_id, frozenset([_norm_club(m.home_team), _norm_club(m.away_team)]))
            groups[key].append(m)

        removidos = 0
        for _, ms in groups.items():
            if len(ms) <= 1:
                continue
            def _rank(x):
                a = str(x.api_id) if x.api_id else ''
                s = 100 if (a.isdigit() and len(a) >= 8) else (50 if a.isdigit() else 0)
                return s + (10 if x.home_score is not None else 0)
            best = max(ms, key=_rank)
            for m in ms:
                if m.id == best.id:
                    continue
                if m.status == 'Live':
                    continue  # nunca apagar ao vivo
                m.delete()
                removidos += 1
        if removidos:
            self.stdout.write(self.style.SUCCESS(f'  🧹 Dedupe: {removidos} duplicatas removidas'))

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
                    'Campeonato Brasileiro Série A': {'name': 'Brasileirão Série A', 'country': 'Brasil'},
                    'Brasileirão Série A': {'name': 'Brasileirão Série A', 'country': 'Brasil'},
                    'Serie B': {'name': 'Brasileirão Série B', 'country': 'Brasil'},
                    'Série B': {'name': 'Brasileirão Série B', 'country': 'Brasil'},
                    'Serie C': {'name': 'Brasileirão Série C', 'country': 'Brasil'},
                    'Série C': {'name': 'Brasileirão Série C', 'country': 'Brasil'},
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
                    # AMBIENTE DE TESTE: nomes como o SofaScore os envia (via Tor)
                    # Brasileirão
                    'Brasileirão Betano': {'name': 'Brasileirão', 'country': 'Brasil'},
                    'Brasileirão Série A': {'name': 'Brasileirão', 'country': 'Brasil'},
                    'Brasileirão Série B': {'name': 'Série B', 'country': 'Brasil'},
                    'Brasileirão Série C': {'name': 'Série C', 'country': 'Brasil'},
                    'Copa Betano do Brasil': {'name': 'Copa do Brasil', 'country': 'Brasil'},
                    'Copa do Brasil': {'name': 'Copa do Brasil', 'country': 'Brasil'},
                    # Liga Europa (nomes atuais do SofaScore)
                    'LaLiga': {'name': 'La Liga', 'country': 'Espanha'},
                    'Liga Portugal Betclic': {'name': 'Primeira Liga', 'country': 'Portugal'},
                    'VriendenLoterij Eredivisie': {'name': 'Eredivisie', 'country': 'Holanda'},
                    'Trendyol Süper Lig': {'name': 'Süper Lig', 'country': 'Turquia'},
                    'Danish Superliga': {'name': 'Superliga', 'country': 'Dinamarca'},
                    'Swiss Super League': {'name': 'Super League', 'country': 'Suica'},
                    'Stoiximan Super League': {'name': 'Super League', 'country': 'Grecia'},
                    'Austrian Bundesliga': {'name': 'Bundesliga', 'country': 'Austria'},
                    'Czech First League': {'name': 'First League', 'country': 'Republica Tcheca'},
                    'Russian Premier League': {'name': 'Premier Liga', 'country': 'Russia'},
                    'Ukrainian Premier League': {'name': 'Premier League', 'country': 'Ucrania'},
                    'Scottish Premiership': {'name': 'Premiership', 'country': 'Escocia'},
                    'J1 League': {'name': 'J1 League', 'country': 'Japao'},
                    'Liga MX, Apertura': {'name': 'Liga MX', 'country': 'Mexico'},
                    # América do Sul
                    'LigaPro Serie A': {'name': 'Liga Pro', 'country': 'Equador'},
                    'LigaPro': {'name': 'Liga Pro', 'country': 'Equador'},
                    'LigaPro Serie B': {'name': 'Serie B', 'country': 'Equador'},
                    'Primera A': {'name': 'Primera A', 'country': 'Colombia'},
                    'Liga de Primera': {'name': 'Primera Division', 'country': 'Chile'},
                    'Liga de Ascenso': {'name': 'Primera B', 'country': 'Chile'},
                    'Liga 1 Te Apuesto': {'name': 'Liga 1', 'country': 'Peru'},
                    'Primera Nacional': {'name': 'Primera B', 'country': 'Argentina'},
                    'Primera División, Apertura': {'name': 'Primera Division', 'country': 'Paraguai'},
                    'Primera División': {'name': 'Primera Division', 'country': 'Paraguai'},  # Paraguai/Uruguai — desambiguado por país
                    'Primera Division': {'name': 'Primera Division', 'country': 'Uruguai'},
                    'Copa Libertadores': {'name': 'Copa Libertadores', 'country': 'America do Sul'},
                    'CONMEBOL Sudamericana': {'name': 'Copa Sul-Americana', 'country': 'America do Sul'},
                    # América do Norte / outros
                    'USL Championship': {'name': 'USL Championship', 'country': 'Estados Unidos'},
                    'MLS': {'name': 'MLS', 'country': 'Estados Unidos'},
                    'Championship': {'name': 'Championship', 'country': 'Inglaterra'},
                    'Norwegian 1st Division': {'name': '1st Division', 'country': 'Noruega'},
                    'Besta deild karla': {'name': 'Besta deild karla', 'country': 'Islandia'},
                    'Iceland 1. deild': {'name': '1. deild', 'country': 'Islandia'},
                    'A-League Men': {'name': 'A-League Men', 'country': 'Australia'},
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
                
                home_name = normalize_team_name(home_name)
                away_name = normalize_team_name(away_name)
                
                # CRITICAL: Validate teams AFTER normalization
                if not is_team_valid_for_league(home_name, league_obj.name):
                    self.stdout.write(self.style.WARNING(f'  🚫 Rejeitado: {home_name} não pertence à {league_obj.name} ({league_obj.country})'))
                    continue
                if not is_team_valid_for_league(away_name, league_obj.name):
                    self.stdout.write(self.style.WARNING(f'  🚫 Rejeitado: {away_name} não pertence à {league_obj.name} ({league_obj.country})'))
                    continue

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
                    
                    # Ligas que seguem o calendário anual (ano exato do jogo = temporada)
                    annual_calendar_countries = [
                        'Brasil', 'Argentina', 'Chile', 'Colombia', 'Equador', 
                        'Paraguai', 'Peru', 'Uruguai', 'Estados Unidos', 'Japao', 
                        'Suecia', 'Noruega', 'Finlandia', 'Islandia', 'Bolivia', 'Venezuela'
                    ]
                    
                    if league_obj.country in annual_calendar_countries:
                        season_year = year
                    else:
                        # Regra Europeia: Agosto a Dezembro pertencem à temporada do ano seguinte
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
                    'ET': 'ET',  # Extra Time (prorrogação)
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

                # GUARD ANTI-ROBO (29/08/2026): o SofaScore entrega temporadas pré-carregadas
                # com status 'finished' e placar para jogos que ainda NÃO aconteceram
                # (ex: sync_upcoming_tor com days_ahead=45 puxa jogos de setembro/outubro
                # que já vêm com resultado simulado). Se a data do jogo ainda não passou,
                # NUNCA aceitar status final/placar — força 'Scheduled' e zera o placar.
                if match_date is not None and status in ('FT', 'Finished', 'AET', 'PEN', 'FINISHED'):
                    now_utc = timezone.now()
                    if match_date > now_utc + timedelta(minutes=30):
                        status = 'Scheduled'
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠️ Guard: jogo futuro ({match_date:%Y-%m-%d %H:%M}) veio com status "{fixture.get("status")}" → forçado Scheduled'
                        ))

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
                    # ANTI-FANTASMA: se este jogo vem de fonte antiga (API-Football desativada —
                    # api_id 7 dígitos na faixa 1490-1499 ou sem id) mas já existe o jogo canônico
                    # do SofaScore (ap_id 8 dígitos 1666/1667) para o MESMO confronto na ~mesma
                    # data (±7 dias), NÃO crie duplicata: atualize o canônico (data/id) e descarte.
                    _aid = str(match_external_id) if match_external_id else ''
                    _is_old = (not _aid) or (_aid.isdigit() and len(_aid) == 7 and _aid.startswith('149'))
                    if _is_old and match_date is not None:
                        try:
                            from datetime import timedelta as _td7
                            _probe = Match.objects.filter(
                                league=league_obj,
                                home_team=home_team,
                                away_team=away_team,
                                date__gte=match_date - _td7(days=7),
                                date__lte=match_date + _td7(days=7),
                            )
                            _canon = None
                            for _p in _probe:
                                _pa = str(_p.api_id) if _p.api_id else ''
                                if _pa.isdigit() and len(_pa) >= 8 and _pa[:4] in ('1666', '1667'):
                                    _canon = _p
                                    break
                            if _canon is not None:
                                _changed = False
                                if _canon.date != match_date:
                                    _canon.date = match_date
                                    _changed = True
                                if not _canon.api_id and match_external_id:
                                    _canon.api_id = match_external_id
                                    _changed = True
                                if _changed:
                                    _canon.save()
                                self.stdout.write(self.style.WARNING(
                                    f'  ⚠️ Fantasma descartado (canônico 8-dígitos existe): {home_team.name} vs {away_team.name}'))
                                count_skipped += 1
                                continue
                        except Exception as _e:
                            self.stdout.write(self.style.WARNING(f'  ⚠️ anti-fantasma check falhou: {_e}'))

                    # Se readonly_structure estiver ativo, NUNCA criamos jogos novos para evitar duplicatas do SofaScore
                    if readonly_structure:
                        self.stdout.write(self.style.WARNING(f'  ⚠️ Ignorado (Read-Only): {home_team.name} vs {away_team.name} não existe no banco.'))
                        continue

                    # Se não achou por ID, cria/atualiza com segurança contra corrida concorrente.
                    # Múltiplos crons (import_odds_api_fixtures 30min + update_live 5min) podem
                    # buscar o MESMO jogo ao mesmo tempo: ambos veem "não existe" e tentam criar
                    # com o mesmo api_id -> 'Duplicate entry'. Aqui priorizamos o api_id como chave
                    # única e, se outro processo ganhar a corrida, apenas atualizamos em vez de quebrar.
                    defaults_no_id = {k: v for k, v in defaults.items() if k != 'api_id'}
                    created = False
                    if match_external_id:
                        try:
                            match_obj, created = Match.objects.update_or_create(
                                api_id=match_external_id,
                                defaults=defaults_no_id
                            )
                        except IntegrityError:
                            # Corrida: outro processo criou este api_id entre nosso check e o create.
                            # OU: o SofaScore está retornando um fixture com api_id diferente
                            # do registro canônico (mesmo jogo, api_id diferente). Tenta re-buscar
                            # por api_id primeiro; se falhar, busca por (date, home, away).
                            match_obj = Match.objects.filter(api_id=match_external_id).first()
                            if not match_obj:
                                # Busca pela constraint unique_match_fixture (date+home+away)
                                match_obj = Match.objects.filter(
                                    date=match_date, home_team=home_team, away_team=away_team
                                ).first()
                            if match_obj:
                                for key, value in defaults_no_id.items():
                                    setattr(match_obj, key, value)
                                match_obj.league = league_obj
                                match_obj.season = season_obj
                                match_obj.home_team = home_team
                                match_obj.away_team = away_team
                                match_obj.save()
                                created = False
                                self.stdout.write(self.style.WARNING(
                                    f'  ⚠️ Duplicata resolvida (atualizei existente): {home_team.name} vs {away_team.name}'))
                            else:
                                # Último recurso: cria com ignore da constraint
                                raise
                    else:
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
                        # AMBIENTE DE TESTE: sem API-Football, standings via SofaScore ainda não implementado — pula sem erro
                        from matches.api_manager import APIManager as _AM
                        if not _AM.USE_API_FOOTBALL:
                            self.stdout.write(self.style.WARNING(f'  ⏭️ recalculate_standings pulado ({lg_name}) — sem API-Football no teste'))
                            continue
                        self.stdout.write(self.style.SUCCESS(f'🧮 Recalculando standings: {lg_name} ({lg_country})'))
                        lg_db = League.objects.filter(name=lg_name, country=lg_country).first()
                        if lg_db:
                            call_command('recalculate_standings', league_id=lg_db.api_id)
                        else:
                            call_command('recalculate_standings', league_id=lg_name)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  ⚠️ Falha ao recalcular {lg_name} ({lg_country}): {e}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️ Não foi possível invocar recalculate_standings: {e}'))
