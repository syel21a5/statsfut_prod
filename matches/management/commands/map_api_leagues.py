import difflib
from django.core.management.base import BaseCommand
from matches.models import League
from matches.api_manager import APIManager
import unicodedata

def remove_accents(input_str):
    if not input_str: return ''
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

class Command(BaseCommand):
    help = 'Mapeia as Ligas do banco de dados (SofaScore) com os IDs da API-Football'

    def handle(self, *args, **options):
        api = APIManager()
        api_config = api.apis.get('api_football_1')
        if not api_config: return
        headers = api._get_headers(api_config)
        base_url = api_config['base_url']

        unmapped_leagues = League.objects.filter(api_id__isnull=True)
        if not unmapped_leagues.exists():
            self.stdout.write(self.style.SUCCESS("Todas as ligas já possuem api_id!"))
            return

        self.stdout.write(self.style.SUCCESS("Buscando lista de ligas na API..."))
        try:
            resp = api._make_request(f"{base_url}/leagues", headers=headers)
            api._increment_usage('api_football_1')
            data = resp.json()
            api_leagues = data.get('response', [])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro na API: {e}"))
            return

        api_league_dict = {}
        for l in api_leagues:
            lname = remove_accents(l['league']['name'])
            lcountry = remove_accents(l['country']['name']) if l['country']['name'] else ''
            
            # País em portugues no banco vs ingles na api (ex: Alemanha vs Germany)
            COUNTRY_MAP = {
                'germany': 'alemanha', 'england': 'inglaterra', 'spain': 'espanha',
                'italy': 'italia', 'france': 'franca', 'brazil': 'brasil',
                'portugal': 'portugal', 'netherlands': 'holanda', 'turkey': 'turquia',
                'denmark': 'dinamarca', 'greece': 'grecia', 'switzerland': 'suica',
                'belgium': 'belgica', 'argentina': 'argentina', 'colombia': 'colombia',
                'chile': 'chile', 'peru': 'peru', 'mexico': 'mexico',
                'australia': 'australia', 'austria': 'austria', 'finland': 'finlandia',
                'norway': 'noruega', 'sweden': 'suecia', 'poland': 'polonia',
                'russia': 'russia', 'ukraine': 'ucrania', 'czech-republic': 'republica tcheca',
                'japan': 'japao'
            }
            lcountry_mapped = COUNTRY_MAP.get(lcountry, lcountry)
            
            key_full = f"{lname}|{lcountry_mapped}"
            api_league_dict[key_full] = l['league']['id']
            if lname not in api_league_dict:
                api_league_dict[lname] = l['league']['id']

        LEAGUE_ALIASES = {
            'brasileirao': 'serie a',
            'serie c': 'serie c',
            'primeira liga': 'primeira liga',
            'copa do brasil': 'copa do brasil',
            'libertadores': 'copa libertadores',
            'copa libertadores': 'copa libertadores'
        }

        for db_league in unmapped_leagues:
            lname = remove_accents(db_league.name)
            lcountry = remove_accents(db_league.country) if db_league.country else ''
            
            search_name = LEAGUE_ALIASES.get(lname, lname)
            key_full = f"{search_name}|{lcountry}"
            
            matched_id = None
            if key_full in api_league_dict:
                matched_id = api_league_dict[key_full]
            elif search_name in api_league_dict:
                matched_id = api_league_dict[search_name]
            else:
                api_keys = list(api_league_dict.keys())
                matches = difflib.get_close_matches(key_full, api_keys, n=1, cutoff=0.7)
                if matches:
                    matched_id = api_league_dict[matches[0]]
                else:
                    matches = difflib.get_close_matches(search_name, api_keys, n=1, cutoff=0.8)
                    if matches:
                        matched_id = api_league_dict[matches[0]]

            if matched_id:
                db_league.api_id = str(matched_id)
                db_league.save(update_fields=['api_id'])
                self.stdout.write(self.style.SUCCESS(f"✅ Liga mapeada: {db_league.name} ({db_league.country}) -> {matched_id}"))
            else:
                self.stdout.write(self.style.WARNING(f"❌ Liga falhou: {db_league.name} ({db_league.country})"))
