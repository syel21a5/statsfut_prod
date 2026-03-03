import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, Season, League

def fix_australia():
    print("=== Corrigindo Season da Austrália ===")
    
    # 1. Encontrar a Liga
    league = League.objects.filter(country__icontains='Australia').first()
    if not league:
        print("Erro: Liga da Austrália não encontrada.")
        return
        
    print(f"Liga Encontrada: {league.name} (ID: {league.id})")
    
    # 2. Season Alvo (2026, pois o cron foi configurado como `--years 2026`)
    season_2026, _ = Season.objects.get_or_create(year=2026)
    print(f"Season Alvo: 2026 (ID: {season_2026.id})")
    
    # 3. Mover todos os jogos desde outubro de 2024 para a Season 2026
    matches_this_season = Match.objects.filter(
        league=league,
        date__gte='2024-10-01'
    )
    
    total_found = matches_this_season.count()
    print(f"Total de jogos encontrados a partir de Out/2024: {total_found}")
    
    matches_this_season.update(season=season_2026)
    print("Todos os jogos foram associados à Season 2026.")
    
    # 4. Remover jogos duplicados (mesmo Home e Away em < 10 dias)
    games = Match.objects.filter(league=league, date__gte='2024-10-01').order_by('home_team', 'away_team', 'date')
    
    to_delete = []
    last_match = None
    
    for m in games:
        if last_match and m.home_team_id == last_match.home_team_id and m.away_team_id == last_match.away_team_id:
            diff = abs((m.date - last_match.date).days)
            if diff <= 10:
                # É duplicata. Prioriza o que tem resultado
                if m.status in ['FT', 'Finished'] and last_match.status not in ['FT', 'Finished']:
                    to_delete.append(last_match.id)
                    last_match = m  # Mantém o mais novo (com resultado)
                else:
                    to_delete.append(m.id)
                    continue # Mantém o antigo
        last_match = m
        
    if to_delete:
        print(f"Removendo {len(to_delete)} jogos duplicados...")
        Match.objects.filter(id__in=to_delete).delete()
    else:
        print("Nenhuma duplicata estrutural encontrada nestes jogos.")
        
    # 5. Forçar recalculação local para a Austrália
    print("\nExecutando recalculate_standings para a Austrália...")
    from django.core.management import call_command
    call_command('recalculate_standings', '--league_name', 'A-League', '--country', 'Australia')

if __name__ == '__main__':
    fix_australia()
