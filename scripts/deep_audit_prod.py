import os
import sys
import django # type: ignore

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League, LeagueStanding, Match # type: ignore

def deep_audit():
    print("--- AUDITORIA PROFUNDA PRODUÇÃO ---")
    
    # 1. Analisar Bragantinos
    brants = Team.objects.filter(name__icontains='Bragantino')
    print(f"\n[Bragantino] Encontrados {brants.count()} times:")
    for b in brants:
        games = Match.objects.filter(django.db.models.Q(home_team=b) | django.db.models.Q(away_team=b)).count()
        standings = LeagueStanding.objects.filter(team=b)
        print(f" - ID: {b.id} | Name: {b.name} | API_ID: {b.api_id} | League: {b.league.name} (ID: {b.league_id}) | Jogos: {games}")
        for s in standings:
            print(f"   -> Standing: Pos {s.position} | League: {s.league.name} (ID: {s.league_id}) | Season: {s.season.year}")

    # 2. Analisar Remo
    remo = Team.objects.filter(name__icontains='Remo').first()
    if remo:
        print(f"\n[Remo] Encontrado:")
        print(f" - ID: {remo.id} | Name: {remo.name} | API_ID: {remo.api_id}")
        # Verificar se o arquivo existe na VPS
        country_slug = django.utils.text.slugify(remo.league.country)
        league_slug = django.utils.text.slugify(remo.league.name)
        path = f"/www/wwwroot/statsfut.com/static/teams/{country_slug}/{league_slug}/{remo.api_id}.png"
        print(f" - Path esperado: {path}")
        print(f" - Arquivo existe: {os.path.exists(path)}")
    else:
        print("\n[Remo] Não encontrado!")

    # 3. Verificar se há ligas do Brasileirão duplicadas
    brasileiroes = League.objects.filter(name__icontains='Brasileira')
    print(f"\n[Ligas] Encontradas {brasileiroes.count()} ligas 'Brasileira':")
    for l in brasileiroes:
        teams_count = Team.objects.filter(league=l).count()
        print(f" - ID: {l.id} | Name: {l.name} | Country: {l.country} | Times: {teams_count}")

if __name__ == '__main__':
    deep_audit()
