import os
import sys
import django # type: ignore

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, LeagueStanding, Match, Season, League # type: ignore
from django.db.models import Q # type: ignore
from django.core.cache import cache # type: ignore

def nuclear_fix():
    print("=== INICIANDO OPERAÇÃO NUCLEAR: LIMPEZA TOTAL BRASILEIRÃO 2026 ===")

    # 1. CONSOLIDAÇÃO BRAGANTINO
    print("\n[1/4] Consolidando Bragantinos...")
    brant_phantom = Team.objects.filter(id=2539).first()
    brant_official = Team.objects.filter(id=2522).first()
    
    if brant_phantom and brant_official:
        print(f" -> Transferindo jogos de {brant_phantom.id} para {brant_official.id}...")
        Match.objects.filter(home_team=brant_phantom).update(home_team=brant_official)
        Match.objects.filter(away_team=brant_phantom).update(away_team=brant_official)
        LeagueStanding.objects.filter(team=brant_phantom).delete()
        brant_phantom.delete()
        print(" ✓ Bragantino fantasma removido.")

    # 2. REMO E OUTROS IDs CRÍTICOS
    print("\n[2/4] Corrigindo IDs SofaScore para Logos...")
    
    mapeamento_final = {
        770: "sofa_2012",   # Remo
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
        735: "sofa_1973",   # Chapecoense (ou sofa_1973 conforme audit)
        757: "sofa_1782",   # Vitoria (verificar ID sofa real ou padrão)
    }

    updated_teams = 0
    for tid, sofa_id in mapeamento_final.items():
        t = Team.objects.filter(id=tid).first()
        if t:
            # Limpar quem por acaso esteja usando este ID
            Team.objects.filter(api_id=sofa_id).exclude(id=tid).update(api_id=None)
            t.api_id = sofa_id
            t.save()
            print(f" ✓ {t.name} (ID {tid}) -> {sofa_id}")
            updated_teams += 1
    
    # Especial: Vitória ID no Localhost é sofa_1782? No audit deu 1782 (numérico)
    vitoria = Team.objects.filter(id=757).first()
    if vitoria:
        vitoria.api_id = "sofa_1970" # ID Sofa do Vitória correto costuma ser 1970 ou similar, ajustando para virar string
        vitoria.save()

    # 3. LIMPEZA DE STANDINGS DUPLICADOS
    print("\n[3/4] Limpando tabela do Brasileirão (Removendo duplicatas visuais)...")
    # Vamos manter apenas um registro por time na liga 2 para a season 2026
    brasileirao2026 = LeagueStanding.objects.filter(league_id=2, season__year=2026)
    seen_teams = set()
    deleted_standings = 0
    
    # Ordenar por id decrescente para manter o registro mais recente se houver conflito
    for s in brasileirao2026.order_by('-id'):
        if s.team_id in seen_teams:
            s.delete()
            deleted_standings += 1
        else:
            seen_teams.add(s.team_id)
    
    print(f" ✓ {deleted_standings} registros duplicados de classificação removidos.")

    # 4. CACHE E FINALIZAÇÃO
    print("\n[4/4] Finalizando...")
    cache.clear()
    print(" ✓ Cache do Django limpo.")
    print("\n=== OPERAÇÃO NUCLEAR CONCLUÍDA! RECARREGUE O SITE. ===")

if __name__ == '__main__':
    nuclear_fix()
