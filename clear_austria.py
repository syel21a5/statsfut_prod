import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League

def clear_austria():
    print("Buscando a liga da Áustria...")
    # Tenta achar a liga pelo nome ou country
    leagues = League.objects.filter(country__icontains='Austria')
    
    if not leagues.exists():
        leagues = League.objects.filter(name__icontains='Bundesliga', country__icontains='Austria')
        
    if not leagues.exists():
        leagues = League.objects.filter(name__icontains='Austria')
        
    if not leagues:
        print("Nenhuma liga da Áustria encontrada no banco de dados.")
        return

    for league in leagues:
        print(f"Encontrada liga: {league.name} (ID: {league.id})")
        
        matches_count = league.matches.count()
        teams_count = league.teams.count()
        standings_count = league.standings.count()
        timings_count = league.goal_timings.count()
        
        print(f"Deletando {matches_count} partidas...")
        league.matches.all().delete()
        
        print(f"Deletando {standings_count} posições da tabela...")
        league.standings.all().delete()
        
        print(f"Deletando {timings_count} estatísticas de tempo de gol...")
        league.goal_timings.all().delete()
        
        print(f"Deletando {teams_count} times...")
        # NOTA: Não estamos mais deletando os times para manter a compatibilidade com logos 
        # e IDs da VPS. O payload_importer vai fazer upsert neles.
        # league.teams.all().delete()
        
        print(f"O mantimento da liga {league.name} foi assegurado.")
        # league.delete()
        
    print("Limpeza das partidas concluída!")

if __name__ == '__main__':
    clear_austria()
