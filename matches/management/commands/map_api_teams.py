import time
import difflib
from datetime import datetime
from django.core.management.base import BaseCommand
from matches.models import League, Team
from matches.api_manager import APIManager
from matches.utils import normalize_team_name

class Command(BaseCommand):
    help = 'Mapeia os times locais (SofaScore) com os IDs da API-Football'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Força atualização mesmo de times que já tem api_id')
        parser.add_argument('--season', type=int, default=datetime.now().year, help='Ano da temporada para buscar os times')
        parser.add_argument('--league_id', type=int, help='ID específico da liga no banco para testar apenas uma liga')

    def handle(self, *args, **options):
        force = options['force']
        season_year = options['season']
        league_id_arg = options.get('league_id')

        # Dicionário de Aliases para tratar nomes difíceis
        # Chave: Nome na API, Valor: Nome no Banco (SofaScore)
        TEAM_ALIASES = {
            'Atletico-GO': 'Atletico Goianiense',
            'Athletico-PR': 'Athletico Paranaense',
            'Red Bull Bragantino': 'Bragantino',
            'Cuiaba': 'Cuiabá',
            'America Mineiro': 'América Mineiro',
            'Vasco Da Gama': 'Vasco da Gama',
            'Sao Paulo': 'São Paulo',
            'Gremio': 'Grêmio',
            'Ceara': 'Ceará',
            'Goias': 'Goiás',
            'Avai': 'Avaí',
            'Coritiba': 'Coritiba',
            'Operario-PR': 'Operário-PR',
            'Sport Recife': 'Sport Recife',
            'Mirassol': 'Mirassol',
            # Adicione outros conforme necessário
        }

        api = APIManager()
        api_config = api.apis.get('api_football_1')
        if not api_config or not api_config.get('key'):
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY não encontrada."))
            return

        headers = api._get_headers(api_config)
        base_url = api_config['base_url']

        if league_id_arg:
            leagues = League.objects.filter(id=league_id_arg, api_id__isnull=False)
        else:
            leagues = League.objects.filter(api_id__isnull=False)

        total_mapped = 0
        total_missed = 0

        for league in leagues:
            self.stdout.write(self.style.SUCCESS(f"\n🌍 Buscando times da liga '{league.name}' (API ID: {league.api_id})..."))
            
            # Buscar times no banco para essa liga
            if force:
                db_teams = Team.objects.filter(league=league)
            else:
                db_teams = Team.objects.filter(league=league, api_id__isnull=True)

            if not db_teams.exists():
                self.stdout.write(f"Todos os times da liga '{league.name}' já possuem api_id! Pulando...")
                continue

            params = {'league': league.api_id, 'season': season_year}
            
            try:
                resp = api._make_request(f"{base_url}/teams", headers=headers, params=params, timeout=15)
                api._increment_usage('api_football_1')
                
                data_json = resp.json()
                if 'errors' in data_json and data_json['errors']:
                    self.stdout.write(self.style.ERROR(f"Erro da API: {data_json['errors']}"))
                    continue
                    
                api_teams_response = data_json.get('response', [])
                if not api_teams_response:
                    self.stdout.write(self.style.WARNING("Nenhum time retornado pela API."))
                    continue
                
                # Criar um dicionário de times da API {nome_normalizado_da_api: api_id}
                api_teams_dict = {}
                for t in api_teams_response:
                    api_t_name = t['team']['name']
                    api_t_id = str(t['team']['id'])
                    
                    # Passa pelo dicionário de aliases
                    mapped_name = TEAM_ALIASES.get(api_t_name, api_t_name)
                    
                    # Guarda os dois mapeamentos (o exato que criamos e o normalizado)
                    api_teams_dict[mapped_name.lower()] = api_t_id
                    api_teams_dict[normalize_team_name(mapped_name).lower()] = api_t_id
                    api_teams_dict[api_t_name.lower()] = api_t_id
                    
                # Pegar nomes das chaves para usar no fuzzy matching
                api_team_names_list = list(api_teams_dict.keys())

                league_mapped = 0
                league_missed = 0

                for db_team in db_teams:
                    db_name_lower = db_team.name.lower()
                    db_norm_lower = normalize_team_name(db_team.name).lower()
                    
                    matched_api_id = None
                    
                    # 1. Match exato direto
                    if db_name_lower in api_teams_dict:
                        matched_api_id = api_teams_dict[db_name_lower]
                    # 2. Match normalizado direto
                    elif db_norm_lower in api_teams_dict:
                        matched_api_id = api_teams_dict[db_norm_lower]
                    else:
                        # 3. Fuzzy Match (Busca Aproximada)
                        matches = difflib.get_close_matches(db_name_lower, api_team_names_list, n=1, cutoff=0.75)
                        if matches:
                            matched_api_id = api_teams_dict[matches[0]]
                        else:
                            # Tenta fuzzy com nome normalizado
                            matches_norm = difflib.get_close_matches(db_norm_lower, api_team_names_list, n=1, cutoff=0.75)
                            if matches_norm:
                                matched_api_id = api_teams_dict[matches_norm[0]]

                    if matched_api_id:
                        if Team.objects.filter(api_id=matched_api_id).exclude(id=db_team.id).exists():
                            self.stdout.write(self.style.WARNING(f"  ⚠️ Ignorado: '{db_team.name}' (ID {matched_api_id} já usado na outra liga)"))
                            league_missed += 1
                        else:
                            db_team.api_id = matched_api_id
                            db_team.save(update_fields=['api_id'])
                            self.stdout.write(self.style.SUCCESS(f"  ✅ Pareado: '{db_team.name}' -> API ID {matched_api_id}"))
                            league_mapped += 1
                            total_mapped += 1
                    else:
                        self.stdout.write(self.style.WARNING(f"  ❌ Falhou: Não encontrou na API para '{db_team.name}'"))
                        league_missed += 1
                        total_missed += 1

                self.stdout.write(f"Resumo da {league.name}: {league_mapped} mapeados, {league_missed} não encontrados.")
                time.sleep(1) # Delay leve para não bater no rate limit
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar liga {league.name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n🏆 Fim da execução! Total de times mapeados: {total_mapped}. Ficaram sem mapear: {total_missed}."))
