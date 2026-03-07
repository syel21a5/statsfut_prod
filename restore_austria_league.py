import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Season, Team
import json

def restore_austria():
    print("RESTORE DA ÁUSTRIA")
    
    # 1. Recria League 44
    league, created_l = League.objects.update_or_create(
        id=44,
        defaults={
            'name': 'Bundesliga',
            'country': 'Austria',
            'logo': '',
            'api_id': '45',  # Tournament ID do SofaScore (Áustria = 45)
            'priority': 0,
            'is_active': True
        }
    )
    if created_l:
        print("Liga 44 (Áustria) recriada com sucesso!")
    else:
        print("Liga 44 já existia (ou foi atualizada).")
        
    # 2. Garante que Season 1 (temporada principal atual no DB de prod) exista 
    # (Embora não devamos forçar o restauro da Season se ela já existe para outras ligas,
    # vamos apenas checar se ela existe. Caso sim, maravilha. Se não, criamos).
    season, created_s = Season.objects.get_or_create(
        id=1,
        defaults={
            'year': 2026,
            'name': '25/26'
        }
    )
    if created_s:
        print("Season 1 recriada com sucesso!")
    
    # IMPORTANTE: Times da Áustria também foram deletados!
    # A Action de import payload só vai CRIA-LOS SE achar as linhas no JSON.
    # Mas como o austria_fixture.json do DB antigo está aqui na VPS, 
    # seria brilhante roda-lo para restaurar as dependências corretas (Team PK e matches velhas).
    # O user tem o arquivo 'import_austria_production.py' já! 
    
    print("\nLIGA PRONTA. Você deve rodar o 'import_austria_production.py' \npara voltar os times antigos e antigas vitórias/estatísticas. \n\nE APÓS ISSO dar Re-run na Action no Github para atualizar com as partidas novas.")

if __name__ == '__main__':
    restore_austria()
