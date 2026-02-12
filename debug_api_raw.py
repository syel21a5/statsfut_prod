import os
import django
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.api_manager import APIManager

def debug_api():
    print("Iniciando debug da API...")
    mgr = APIManager()
    
    # Tenta buscar via Football-Data.org (PL = 2021)
    # Verifica o que a API retorna
    
    # Configuração manual para garantir teste
    # Usando a chave que funcionou no log anterior (api_1)
    # Mas o APIManager já deve pegar do env
    
    try:
        # Chama o método interno para ver o raw response se possível, ou o método público
        print("Chamando get_upcoming_fixtures...")
        fixtures = mgr.get_upcoming_fixtures(league_ids=[39], days_ahead=15)
        print(f"Fixtures retornadas: {len(fixtures)}")
        for f in fixtures:
            print(f" - {f['home_team']} vs {f['away_team']} ({f['date']}) [{f['status']}]")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    debug_api()
