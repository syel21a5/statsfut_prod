import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League

def clear_australia():
    print("Buscando a liga A-League Men (ID 21)...")
    try:
        league = League.objects.get(id=21)
    except League.DoesNotExist:
        print("Erro: Liga 21 não encontrada!")
        return

    print(f"Liga: {league.name}")
    print(f"Limpando {league.matches.count()} partidas...")
    league.matches.all().delete()
    
    print(f"Limpando {league.standings.count()} posições da tabela...")
    league.standings.all().delete()
    
    print(f"Limpando {league.goal_timings.count()} estatísticas de tempo de gol...")
    league.goal_timings.all().delete()
    
    # ATENÇÃO: NÃO deletamos a liga e nem os times, para não quebrar a vinculação
    # dos logos (/static/teams/australia/a-league-men/sofa_XXXX.png)
    
    print("Limpeza de partidas e pontuações da Austrália concluída!")

if __name__ == '__main__':
    clear_australia()
