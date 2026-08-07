import os
import sys
import django # type: ignore

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, LeagueStanding, Match, Season, League # type: ignore
from django.db.models import Q # type: ignore
from django.core.cache import cache # type: ignore

def nuclear_cleanup_production():
    print("=== INICIANDO OPERAÇÃO NUCLEAR: LIMPEZA TOTAL E RESGATE DO BRASILEIRÃO 2026 ===")

    # 1. MAPEAMENTO DEFINITIVO (SÉRIE A 2026)
    mapeamento_final = {
        747: "sofa_1981",   # São Paulo
        746: "sofa_1957",   # Corinthians
        737: "sofa_1963",   # Palmeiras
        748: "sofa_5981",   # Flamengo
        744: "sofa_1966",   # Internacional
        739: "sofa_1961",   # Fluminense
        741: "sofa_5926",   # Grêmio
        2526: "sofa_1977",  # Vasco
        745: "sofa_1954",   # Cruzeiro
        2521: "sofa_1976",  # Atletico-MG
        2495: "sofa_1967",  # Athletico (PR)
        736: "sofa_1984",   # Coritiba
        752: "sofa_1968",   # Santos
        755: "sofa_1958",   # Botafogo
        759: "sofa_1955",   # Bahia
        764: "sofa_2020",   # Fortaleza
        769: "sofa_21982",  # Mirassol
        735: "sofa_1973",   # Chapecoense
        757: "sofa_1970",   # Vitória
        770: "sofa_2012",   # Remo
        2522: "sofa_1999",  # Red Bull Bragantino
    }

    # 2. LIMPEZA PREVENTIVA DE IDs (EVITAR INTEGRITY ERROR)
    print("\n[1/4] Limpando APIs IDs antigos para evitar conflitos...")
    all_target_sofa_ids = list(mapeamento_final.values())
    
    # Limpa QUALQUER time que esteja usando esses IDs SofaScore, globalmente
    conflicting_teams = Team.objects.filter(api_id__in=all_target_sofa_ids)
    print(f" -> Encontrados {conflicting_teams.count()} times com IDs SofaScore conflitantes. Limpando...")
    conflicting_teams.update(api_id=None)
    print(" ✓ Terreno preparado (IDs zerados).")

    # 3. APLICAÇÃO DOS NOVOS IDs E CONSOLIDAÇÃO
    print("\n[2/4] Aplicando IDs oficiais e limpando fantasmas...")
    
    # Bragantino Fantasma ID 2539 (Audit mostrou que ele existe e atrapalha)
    brant_phantom = Team.objects.filter(id=2539).first()
    brant_official = Team.objects.filter(id=2522).first()
    if brant_phantom and brant_official:
        print(f" -> Movendo jogos do Bragantino {brant_phantom.id} para o Oficial {brant_official.id}")
        Match.objects.filter(home_team=brant_phantom).update(home_team=brant_official)
        Match.objects.filter(away_team=brant_phantom).update(away_team=brant_official)
        LeagueStanding.objects.filter(team=brant_phantom).delete()
        brant_phantom.delete()
        print(" ✓ Bragantino fantasma deletado.")

    for tid, sofa_id in mapeamento_final.items():
        t = Team.objects.filter(id=tid).first()
        if t:
            t.api_id = sofa_id
            t.save()
            print(f" ✓ {t.name} (ID {tid}) -> {sofa_id}")
        else:
            print(f" ? Time ID {tid} não encontrado no banco.")

    # 4. LIMPEZA DA TABELA (STANDINGS) - MANTER APENAS 2026
    print("\n[3/4] Limpando classificações antigas (2015-2025) do Brasileirão...")
    # O audit mostrou que o Brasileirão é a liga ID 2
    old_standings = LeagueStanding.objects.filter(league_id=2).exclude(season__year=2026)
    count_old = old_standings.count()
    old_standings.delete()
    print(f" ✓ {count_old} registros de anos anteriores removidos da tabela.")

    # Remover duplicidade dentro do próprio ano de 2026 se houver
    standings_2026 = LeagueStanding.objects.filter(league_id=2, season__year=2026)
    seen_teams = set()
    dup_count = 0
    for s in standings_2026.order_by('-id'):
        if s.team_id in seen_teams:
            s.delete()
            dup_count += 1
        else:
            seen_teams.add(s.team_id)
    print(f" ✓ {dup_count} duplicatas do ano 2026 removidas.")

    # 5. CACHE E FINALIZAÇÃO
    print("\n[4/4] Limpando Cache...")
    cache.clear()
    print(" ✓ Cache limpo.")
    print("\n=== OPERAÇÃO CONCLUÍDA! O SITE ESTÁ LIMPO E COM DADOS DE 2026. ===")

if __name__ == '__main__':
    nuclear_cleanup_production()
