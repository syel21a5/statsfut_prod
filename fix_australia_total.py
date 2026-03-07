import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, League, Season
from django.db.models import Q

def fix_australia():
    print("--- MEGA FIX AUSTRÁLIA (PRODUÇÃO) ---")
    
    # 1. Obter Liga 21
    try:
        league = League.objects.get(id=21)
    except League.DoesNotExist:
        print("Erro: Liga 21 não encontrada!")
        return

    # 2. Mapa Master de Times (13 TIMES - A-League Men 2025/26)
    # Incluindo Western United e Auckland
    master_teams = {
        "sofa_2934": "Newcastle Jets FC",
        "sofa_800224": "Auckland FC",
        "sofa_5971": "Sydney FC",
        "sofa_2946": "Adelaide United",
        "sofa_5970": "Melbourne Victory",
        "sofa_5966": "Central Coast Mariners",
        "sofa_371682": "Macarthur FC",
        "sofa_72926": "Western Sydney Wanderers",
        "sofa_5968": "Brisbane Roar",
        "sofa_42210": "Melbourne City",
        "sofa_2945": "Perth Glory",
        "sofa_7568": "Wellington Phoenix",
        "sofa_342935": "Western United"
    }

    print("\nSincronizando 13 times e IDs SofaScore...")
    for api_id, clean_name in master_teams.items():
        team, created = Team.objects.update_or_create(
            api_id=api_id,
            defaults={'name': clean_name, 'league': league}
        )
        if created:
            print(f"  [NOVO] Time criado: {clean_name}")
        else:
            print(f"  [OK] Time atualizado: {clean_name}")

    # 3. Limpeza de "Sujeira" (Jogos sem api_id ou duplicados)
    print("\nLimpando partidas antigas para re-importação limpa...")
    Match.objects.filter(league=league).delete()
    print("Partidas limpas.")

    # 4. Ajustar Classificação (Zerar para forçar recálculo)
    league.standings.all().delete()
    print("Tabela limpa.")

    print("\nPRONTO! O servidor agora conhece os 13 times e os nomes estão padronizados.")
    print("RECOMENDAÇÃO: Rode o 'Re-run jobs' da Austrália no GitHub agora.")

if __name__ == '__main__':
    fix_australia()
