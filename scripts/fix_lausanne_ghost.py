import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, LeagueStanding, League

def fix_lausanne():
    print("Iniciando limpeza do time fantasma Lausanne...")
    
    # 1. Encontrar a liga Suíça (ID 40 ou pelo nome)
    league = League.objects.filter(id=40).first()
    if not league:
        league = League.objects.filter(country='Suica', name='Super League').first()
    
    if not league:
        print("Erro: Liga Suica não encontrada!")
        return

    print(f"Liga: {league.name} ({league.country})")

    # 2. Identificar o time fantasma
    # O time real geralmente é "FC Lausanne-Sport" (sofa_2463)
    # O fantasma é "Lausanne" (sofa_2451) com 0 pontos
    phantom = Team.objects.filter(league=league, name='Lausanne', api_id='sofa_2451').first()
    
    if not phantom:
        print("Time fantasma 'Lausanne' não identificado (pode já ter sido removido).")
    else:
        print(f"Encontrado: {phantom.name} (ID: {phantom.id}, API: {phantom.api_id})")
        
        # 3. Remover Standings
        standings = LeagueStanding.objects.filter(team=phantom)
        count = standings.count()
        standings.delete()
        print(f"Sucesso: {count} registros de classificação removidos para o time {phantom.name}.")

    # 4. Verificar se a tabela agora tem 12 times
    final_count = LeagueStanding.objects.filter(league=league).values('team').distinct().count()
    print(f"Final: A liga agora tem {final_count} times distintos na classificação.")

if __name__ == "__main__":
    fix_lausanne()
