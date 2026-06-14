import os
import time
import difflib
import unicodedata
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db.models import Q

from matches.models import League, Team, Match
from matches.api_manager import APIManager

# =============================================================================
# DICIONÁRIO UNIVERSAL DE TIMES
# Mapeia o nome no banco (normalizado, sem acentos, lowercase) para o nome na API.
# Construído manualmente comparando DB vs API time a time, liga por liga.
# =============================================================================
TEAM_ALIASES = {
    # --- NORUEGA 1. Division ---
    'odds bk': 'odd ballklubb',
    'stabaek fotball': 'stabaek',
    'hodd il': 'hodd',
    'strommen if': 'strommen',
    'ranheim il': 'ranheim',
    'moss fk': 'moss',
    'sogndal il': 'sogndal',
    'bryne fk': 'bryne',
    'lyn fk': 'lyn',

    # --- BRASIL Série A ---
    'vasco': 'vasco da gama',
    'athletico': 'atletico paranaense',
    'bragantino': 'rb bragantino',

    # --- BRASIL Série B ---
    'gremio novorizontino': 'novorizontino',
    'vila nova fc': 'vila nova',
    'nautico': 'nautico recife',
    'clube de regatas brasil': 'crb',
    'botafogo sp': 'botafogo sp',
    'paysandu sc': 'paysandu',
    'amazonas fc': 'amazonas',

    # --- BRASIL Série C ---
    'maranhao ac': 'maranhao',
    'maringá fc': 'maringa',
    'ypiranga fc': 'ypiranga rs',
    'barra fc': 'barra',
    'sampaio correa': 'sampaio correa',
    'aa aparecidense': 'aparecidense',

    # --- ARGENTINA Liga Profesional ---
    'arsenal sarandi': 'arsenal de sarandi',
    'arsenal de sarandi': 'arsenal de sarandi',
    'union de santa fe': 'union santa fe',
    'club atletico colon': 'colon',
    'san martin t.': 'san martin de tucuman',
    'san martin s.j.': 'san martin de san juan',
    'san martin de san juan': 'san martin de san juan',
    'godoy cruz': 'godoy cruz',

    # --- CHILE Primera Division ---
    'universidad catolica': 'u. catolica',
    'everton de vina del mar': 'everton de vina',
    'audax italiano': 'a. italiano',
    'deportes la serena': 'd. la serena',
    'deportes concepcion': 'concepcion',

    # --- CHILE Primera B ---
    'club deportes antofagasta': 'antofagasta',
    'deportes magallanes': 'magallanes',
    'deportes recoleta': 'recoleta',
    'san luis de quillota': 'san luis',
    'deportes puerto montt': 'd. puerto montt',
    'santiago morning': 'santiago morning',
    'ac barnechea': 'barnechea',

    # --- COLOMBIA Primera A ---
    'junior barranquilla': 'junior',
    'boyaca chico fc': 'chico',
    'cucuta deportivo': 'cucuta',
    'envigado fc': 'envigado',
    'patriotas boyaca': 'patriotas',
    'union magdalena': 'union magdalena',
    'atletico bucaramanga': 'bucaramanga',
    'alianza valledupar fc': 'alianza valledupar',
    'rionegro aguilas doradas': 'aguilas doradas',
    'jaguares de cordoba': 'jaguares',
    'atletico huila': 'atletico huila',
    'alianza petrolera': 'alianza petrolera',
    'independiente santa fe': 'santa fe',
    'internacional de palmira': 'internacional de palmira',

    # --- ITALIA Serie A ---
    'roma': 'as roma',
    'milan': 'ac milan',
    'ssc napoli': 'napoli',
    'verona': 'hellas verona',

    # --- MEXICO Liga MX ---
    'pumas unam': 'u.n.a.m.   pumas',
    'cd guadalajara': 'guadalajara chivas',
    'club leon': 'leon',
    'club puebla': 'puebla',
    'queretaro fc': 'club queretaro',
    'club necaxa': 'necaxa',
    'cd toluca': 'toluca',
    'atlas fc': 'atlas',
    'cf monterrey': 'monterrey',
    'mazatlan fc': 'mazatlan',

    # --- PERU Liga 1 ---
    'universidad tecnica de cajamarca': 'utc cajamarca',
    'universitario de deportes': 'universitario',
    'ad cantolao': 'cantolao',
    'deportivo municipal': 'municipal',
    'deportivo usmp': 'usmp',
    'fc carlos stein': 'carlos stein',
    'deportivo llacuabamba': 'llacuabamba',
    'asociacion deportiva tarma': 'adt',
    'union comercio': 'union comercio',
    'los chankas cyc': 'club deportivo los chankas',
    'comerciantes unidos': 'comerciantes unidos',
    'cd juan pablo ii': 'juan pablo ii college',
    'cd moquegua': 'ucv moquegua',
    'fc cajamarca': 'fc cajamarca',
    'cusco fc': 'cusco',
    'alianza atletico de sullana': 'alianza atletico',
    'club atletico grau': 'atletico grau',

    # --- PORTUGAL Primeira Liga ---
    'sporting braga': 'sc braga',
    'vitoria sc': 'guimaraes',
    'cd nacional': 'nacional',
    'estoril praia': 'estoril',
    'fc arouca': 'arouca',
    'cf estrela amadora': 'estrela',
    'fc alverca': 'alverca',
    'chaves': 'chaves', # maybe not in api
    'portimonense sad': 'portimonense',
    
    # --- RUSSIA Premier Liga ---
    'cska moskva': 'cska moscow',
    'spartak moskva': 'spartak moscow',
    'zenit st. petersburg': 'zenit',
    'lokomotiv moskva': 'lokomotiv',
    'dinamo moskva': 'dynamo',
    'rostov': 'fc rostov',
    'krasnodar': 'fc krasnodar',
    'ural yekaterinburg': 'ural',
    'krylya sovetov': 'krylia sovetov',
    'akhmat grozny': 'akhmat',
    'sochi': 'fc sochi',
    'nizhny novgorod': 'nizhny novgorod',
    'baltika kaliningrad': 'baltika',
}

# =============================================================================
# LISTA NEGRA: Mapeamentos que o fuzzy matching tentaria fazer ERRADO.
# Se o nome normalizado do time no banco estiver aqui, o fuzzy matching é ignorado.
# O time só será mapeado se estiver no TEAM_ALIASES acima.
# =============================================================================
FUZZY_BLACKLIST = {
    'chacarita juniors',    # NÃO é Boca Juniors
    'atletico goianiense',  # NÃO é Atletico Paranaense (no Brasileirão)
    'criciuma',             # NÃO é Coritiba (no Brasileirão, mas é na Série B)
    'empoli',               # NÃO é Napoli
    'spezia',               # NÃO é Venezia
    'crotone',              # NÃO é Frosinone
    'deportes recoleta',    # NÃO é Deportes Temuco
    'deportes concepcion',  # NÃO é Deportes Copiapó (na Primera B Chile)
    'deportes la serena',   # NÃO é Deportes Santa Cruz (na Primera B Chile)
    'deportes limache',     # NÃO é Deportes Temuco (na Primera B Chile)
    'atletico huila',       # NÃO é Atletico Nacional
    'independiente santa fe', # NÃO é Independiente Medellin
    'alianza petrolera',    # NÃO é Alianza Valledupar
    'internacional de palmira', # NÃO é Internacional de Bogota
    'mazatlan fc',          # NÃO é Atlante FC
    'atlas fc',             # NÃO é Atlante FC
    'universidad catolica', # NÃO é Universidad de Chile
    'ferroviario',          # NÃO é Ferroviária (são times diferentes)
}

# =============================================================================
# CORREÇÕES DE LIGAS: IDs que foram mapeados errado pelo fuzzy matching.
# Formato: {api_id_errado: api_id_correto}
# =============================================================================
LEAGUE_FIXES = {
    '1229': '281',  # Peru Liga 1: era feminina (1229), correto é masculina (281)
}


def normalize_name(name):
    """Remove acentos e caracteres especiais, aplica aliases."""
    n = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8').lower().strip()
    n = n.replace('-', ' ')
    return TEAM_ALIASES.get(n, n)


class Command(BaseCommand):
    help = 'Mapeamento Econômico e Inteligente de IDs do SofaScore para API-Football'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando Mapeador Inteligente de IDs..."))
        api = APIManager()
        api_config = api.apis.get('api_football_1')
        if not api_config or not api_config.get('key'):
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY não configurada!"))
            return
            
        headers = api._get_headers(api_config)
        credits_used = 0
        
        # 0. CORRIGIR LIGAS COM ID ERRADO
        for wrong_id, correct_id in LEAGUE_FIXES.items():
            fixed = League.objects.filter(api_id=wrong_id).update(api_id=correct_id)
            if fixed:
                self.stdout.write(self.style.SUCCESS(f"🔧 Liga corrigida: API ID {wrong_id} -> {correct_id}"))

        # 1. MAPEAMENTO DE LIGAS (Por País)
        self.stdout.write(self.style.WARNING("\n--- ETAPA 1: MAPEAMENTO DE LIGAS ---"))
        leagues_to_map = League.objects.filter(Q(api_id__isnull=True) | Q(api_id__startswith='sofa_'))
        countries = list(leagues_to_map.values_list('country', flat=True).distinct())
        
        self.stdout.write(f"Encontradas {leagues_to_map.count()} ligas precisando de mapeamento em {len(countries)} países.")
        
        for country in countries:
            if not country: continue
            
            self.stdout.write(f"Buscando ligas da API para o país: {country}")
            resp = api._make_request(f"{api_config['base_url']}/leagues", headers=headers, params={'country': country}, timeout=15)
            credits_used += 1
            time.sleep(1)
            
            if resp.status_code == 200:
                data = resp.json().get('response', [])
                api_leagues = [{'id': str(item['league']['id']), 'name': item['league']['name'], 'type': item['league'].get('type', '')} for item in data]
                
                db_leagues_country = leagues_to_map.filter(country=country)
                for db_l in db_leagues_country:
                    best_match = None
                    best_score = 0
                    for al in api_leagues:
                        # Ignorar ligas femininas e copas
                        if 'women' in al['name'].lower() or 'w ' in al['name'].lower():
                            continue
                        score = difflib.SequenceMatcher(None, db_l.name.lower(), al['name'].lower()).ratio()
                        if score > best_score:
                            best_score = score
                            best_match = al
                    
                    if best_match and best_score > 0.60:
                        db_l.api_id = best_match['id']
                        db_l.save()
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Liga mapeada: {db_l.name} -> {best_match['id']}"))
            else:
                self.stdout.write(self.style.ERROR(f"  X Falha ao buscar ligas para {country}"))

        # 2. MAPEAMENTO DE TIMES E PARTIDAS (Por Liga)
        self.stdout.write(self.style.WARNING("\n--- ETAPA 2 e 3: MAPEAMENTO DE TIMES E PARTIDAS ---"))
        current_year = datetime.now().year
        
        valid_leagues = League.objects.exclude(api_id__isnull=True).exclude(api_id__startswith='sofa_')
        
        for league in valid_leagues:
            teams_to_map = league.teams.filter(Q(api_id__isnull=True) | Q(api_id__startswith='sofa_'))
            matches_to_map = Match.objects.filter(
                Q(home_team__league=league) | Q(away_team__league=league),
                date__gte=now() - timedelta(days=15),
                date__lte=now() + timedelta(days=60)
            ).filter(Q(api_id__isnull=True) | Q(api_id__startswith='sofa_')).distinct()
            
            if not teams_to_map.exists() and not matches_to_map.exists():
                continue
                
            self.stdout.write(f"\nLiga: {league.name} (API ID: {league.api_id})")
            
            # --- MAPEAMENTO DE TIMES ---
            if teams_to_map.exists():
                self.stdout.write(f"  -> Mapeando {teams_to_map.count()} times...")
                
                # Tentar temporada atual e anterior
                api_t_list = []
                for season_try in [current_year, current_year - 1]:
                    resp_t = api._make_request(f"{api_config['base_url']}/teams", headers=headers, params={'league': league.api_id, 'season': season_try}, timeout=15)
                    credits_used += 1
                    time.sleep(0.5)
                    
                    if resp_t.status_code == 200:
                        api_teams = resp_t.json().get('response', [])
                        if api_teams:
                            api_t_list = [{'id': str(t['team']['id']), 'name': t['team']['name']} for t in api_teams]
                            break
                
                if not api_t_list:
                    self.stdout.write(self.style.WARNING(f"  ⚠ API não retornou times para esta liga."))
                    continue
                    
                for db_t in teams_to_map:
                    db_t_norm = normalize_name(db_t.name)
                    
                    # PASSO 1: Tentar match exato pelo dicionário/normalização
                    exact_match = None
                    for at in api_t_list:
                        at_norm = normalize_name(at['name'])
                        if db_t_norm == at_norm:
                            exact_match = at
                            break
                    
                    if exact_match:
                        try:
                            db_t.api_id = exact_match['id']
                            db_t.name = exact_match['name']
                            db_t.save()
                            self.stdout.write(self.style.SUCCESS(f"    ✓ EXATO: {db_t.name} -> {exact_match['id']}"))
                        except Exception:
                            self.stdout.write(self.style.WARNING(f"    ! Duplicado: {db_t.name} (ID {exact_match['id']})"))
                        continue
                    
                    # PASSO 2: Fuzzy matching com threshold ALTO (85%) e checagem de blacklist
                    if db_t_norm in FUZZY_BLACKLIST:
                        self.stdout.write(self.style.WARNING(f"    ⛔ Blacklist: '{db_t.name}' - fuzzy desativado (precisa entrada no dicionário)"))
                        continue
                    
                    best_t_match = None
                    best_t_score = 0
                    for at in api_t_list:
                        at_norm = normalize_name(at['name'])
                        score = difflib.SequenceMatcher(None, db_t_norm, at_norm).ratio()
                        if score > best_t_score:
                            best_t_score = score
                            best_t_match = at
                    
                    if best_t_match and best_t_score > 0.85:
                        try:
                            db_t.api_id = best_t_match['id']
                            db_t.name = best_t_match['name']
                            db_t.save()
                            self.stdout.write(self.style.SUCCESS(f"    ✓ FUZZY ({best_t_score:.0%}): {db_t.name} -> {best_t_match['id']}"))
                        except Exception:
                            self.stdout.write(self.style.WARNING(f"    ! Duplicado: {db_t.name} (ID {best_t_match['id']})"))
                    else:
                        closest_name = best_t_match['name'] if best_t_match else 'Nenhum'
                        closest_id = best_t_match['id'] if best_t_match else 'N/A'
                        self.stdout.write(self.style.ERROR(f"    X NÃO MAPEADO: '{db_t.name}' (Mais próximo: '{closest_name}' ID:{closest_id} Score:{best_t_score:.0%})"))

            # --- MAPEAMENTO DE PARTIDAS ---
            if matches_to_map.exists():
                self.stdout.write(f"  -> Mapeando {matches_to_map.count()} partidas recentes/futuras...")
                resp_m = api._make_request(f"{api_config['base_url']}/fixtures", headers=headers, params={'league': league.api_id, 'season': current_year}, timeout=15)
                credits_used += 1
                time.sleep(1)
                
                if resp_m.status_code == 200:
                    api_fixtures = resp_m.json().get('response', [])
                    
                    for db_m in matches_to_map:
                        db_h_name = normalize_name(db_m.home_team.name)
                        db_a_name = normalize_name(db_m.away_team.name)
                        
                        found = False
                        for f in api_fixtures:
                            api_h_name = normalize_name(f['teams']['home']['name'])
                            api_a_name = normalize_name(f['teams']['away']['name'])
                            
                            match_h = (db_h_name in api_h_name) or (api_h_name in db_h_name)
                            match_a = (db_a_name in api_a_name) or (api_a_name in db_a_name)
                            
                            if match_h and match_a:
                                try:
                                    db_m.api_id = str(f['fixture']['id'])
                                    db_m.save()
                                    self.stdout.write(self.style.SUCCESS(f"    ✓ Partida mapeada: {db_m.home_team.name} x {db_m.away_team.name} -> {f['fixture']['id']}"))
                                except Exception:
                                    self.stdout.write(self.style.WARNING(f"    ! Partida duplicada: {db_m.home_team.name} x {db_m.away_team.name}"))
                                found = True
                                break
                        
                        if not found:
                            self.stdout.write(self.style.WARNING(f"    X Partida não encontrada: {db_m.home_team.name} x {db_m.away_team.name}"))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 MAPEAMENTO CONCLUÍDO!"))
        self.stdout.write(self.style.SUCCESS(f"💰 Créditos consumidos: {credits_used}"))
