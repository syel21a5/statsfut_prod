import os
import sys
import django # type: ignore
from django.utils.text import slugify # type: ignore

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, LeagueStanding, Match, League, Season # type: ignore
from django.db.models import Q # type: ignore

def verify_prod_state():
    print("=== VERIFICAÇÃO DE ESTADO REAL (VPS) ===")
    
    # 1. Contagem de times no Brasileirão 2026
    league = League.objects.get(id=2)
    season = Season.objects.get(year=2026)
    standings = LeagueStanding.objects.filter(league=league, season=season).order_by('position')
    
    print(f"\nLiga: {league.name} (ID: {league.id}) | Temporada: {season.year}")
    print(f"Total de times na tabela: {standings.count()}")
    
    # 2. Verificar arquivos de logo
    print("\n[Verificação de Arquivos .png]")
    teams_to_check = [
        (747, "São Paulo"),
        (770, "Remo"),
        (2522, "RB Bragantino"),
        (2521, "Atlético-MG"),
        (755, "Botafogo")
    ]
    
    base_path = "/www/wwwroot/statsfut.com/static/teams/brasil/brasileirao/"
    
    for tid, name in teams_to_check:
        t = Team.objects.filter(id=tid).first()
        if t:
            file_path = os.path.join(base_path, f"{t.api_id}.png")
            exists = os.path.exists(file_path)
            print(f" -> {name:15} | API: {t.api_id:12} | File: {exists} | Path: {file_path}")
        else:
            print(f" !! Time {name} (ID {tid}) NÃO ENCONTRADO.")

    # 3. Investigar o "Bragantino" 2539 (O fantasma)
    ghost = Team.objects.filter(id=2539).first()
    if ghost:
        print(f"\n!! ALERTA: O Fantasma (ID 2539) AINDA EXISTE: {ghost.name}")
        stds = LeagueStanding.objects.filter(team=ghost)
        print(f"    Standings do Fantasma: {stds.count()}")
    else:
        print("\n✓ O Fantasma (ID 2539) foi realmente deletado do banco.")

    # 4. Checar Slugs das Ligas
    print(f"\nSlugify(League Name): {slugify(league.name)}")

if __name__ == '__main__':
    verify_prod_state()
