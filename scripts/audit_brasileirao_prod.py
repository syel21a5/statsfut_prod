import os
import sys
import django # type: ignore
from django.utils.text import slugify # type: ignore

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, LeagueStanding, Match # type: ignore
from django.db.models import Q # type: ignore

def final_audit():
    print("=== AUDITORIA CIRÚRGICA: BRASILEIRÃO 2026 (PRODUÇÃO) ===")
    
    # 1. Pegar a tabela atual
    # Nota: Vamos filtrar por temporada 2026 se possível, ou apenas a liga
    standings = LeagueStanding.objects.filter(
        league__country__icontains='Brasil', 
        league__name__icontains='Brasileira'
    ).select_related('team', 'league').order_by('position')

    if not standings.exists():
        print("!! Nenhuma classificação encontrada para o Brasileirão.")
        return

    print(f"\nPos | Time (ID) | API_ID | Slug (Calc) | Logo Path")
    print("-" * 90)
    
    base_static = "/www/wwwroot/statsfut.com/static/teams/brasil/brasileirao/"
    
    for s in standings:
        t = s.team
        calc_slug = slugify(t.name)
        logo_file = f"{t.api_id}.png" if t.api_id else "N/A"
        logo_exists = os.path.exists(os.path.join(base_static, logo_file)) if t.api_id else False
        
        status = "✓" if logo_exists else "X (FALTANDO)"
        print(f"{s.position:2} | {t.name[:20]:20} ({t.id:4}) | {t.api_id:10} | {calc_slug:20} | {status}")

    # 2. Investigar o Remo especificamente
    print("\n[Investigação REMO]")
    remos = Team.objects.filter(name__icontains='Remo')
    for r in remos:
        games = Match.objects.filter(Q(home_team=r) | Q(away_team=r)).count()
        print(f" -> ID: {r.id} | Name: {r.name} | API: {r.api_id} | Slug: {slugify(r.name)} | Games: {games}")

    # 3. Investigar Bragantinos
    print("\n[Investigação BRAGANTINO]")
    brants = Team.objects.filter(name__icontains='Bragantino')
    for b in brants:
        games = Match.objects.filter(Q(home_team=b) | Q(away_team=b)).count()
        print(f" -> ID: {b.id} | Name: {b.name} | API: {b.api_id} | Slug: {slugify(b.name)} | Games: {games}")

if __name__ == '__main__':
    final_audit()
