import os
import sys
import django # type: ignore
from django.db.models import Q # type: ignore

# Configuração do Django na VPS
sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League, LeagueStanding, Match # type: ignore

def super_fix():
    print("=== INICIANDO REPARO DEFINITIVO NA PRODUÇÃO ===")
    
    # 1. LIMPEZA DO BRAGANTINO DUPLICADO
    print("\n[1/2] Limpando duplicados do Bragantino...")
    all_brants = Team.objects.filter(name__icontains='Bragantino').order_by('-id')
    if all_brants.count() sail_count := all_brants.count() > 1:
        official = None
        garbage = []
        
        # Vamos definir como oficial o que tiver mais jogos vinculados
        for b in all_brants:
            games = Match.objects.filter(Q(home_team=b) | Q(away_team=b)).count()
            print(f" -> Time: {b.name} (ID: {b.id}) - Jogos: {games}")
            if official is None or games > Match.objects.filter(Q(home_team=official) | Q(away_team=official)).count():
                if official: garbage.append(official)
                official = b
            else:
                garbage.append(b)
        
        if official:
            print(f" >> OFICIAL DEFINIDO: {official.name} (ID: {official.id})")
            official.name = "Red Bull Bragantino"
            official.api_id = "sofa_1999"
            official.save()
            
            for g in garbage:
                print(f" >> Removendo duplicado: {g.name} (ID: {g.id})")
                # Transferir jogos que por acaso estejam no duplicado
                Match.objects.filter(home_team=g).update(home_team=official)
                Match.objects.filter(away_team=g).update(away_team=official)
                # Remover das classificações
                LeagueStanding.objects.filter(team=g).delete()
                # Deletar o time fantasma
                g.delete()
    else:
        print(" -> Nenhum duplicado de Bragantino detectado.")

    # 2. REPARO DE IDs DO BRASILEIRÃO (LOGOS)
    print("\n[2/2] Forçando IDs SofaScore para o Brasileirão...")
    
    # Mapeamento robusto filtrado por país
    mapeamento = {
        'Flamengo': 'sofa_5981',
        'Sao Paulo': 'sofa_1981',
        'São Paulo': 'sofa_1981',
        'Palmeiras': 'sofa_1963',
        'Corinthians': 'sofa_1957',
        'Fluminense': 'sofa_1961',
        'Gremio': 'sofa_5926',
        'Grêmio': 'sofa_5926',
        'Internacional': 'sofa_1966',
        'Botafogo': 'sofa_1958',
        'Santos': 'sofa_1968',
        'Vasco': 'sofa_1977',
        'Cruzeiro': 'sofa_1954',
        'Atletico-MG': 'sofa_1976',
        'Athletico': 'sofa_1967',
        'Bahia': 'sofa_1955',
        'Fortaleza': 'sofa_2020',
        'Cuiaba': 'sofa_37803',
        'Juventude': 'sofa_1980',
        'Ceara': 'sofa_2001',
        'Sport': 'sofa_1959',
        'Mirassol': 'sofa_21982',
        'Chapecoense': 'sofa_1973',
        'Coritiba': 'sofa_1984',
        'Americo Mineiro': 'sofa_1971',
        'Joinville': 'sofa_1985',
        'Parana': 'sofa_1965',
        'Figueirense': 'sofa_1970',
        'Red Bull Bragantino': 'sofa_1999',
    }

    brasileirao = League.objects.filter(country__icontains='Brasil', name__icontains='Brasileira').first()
    if brasileirao:
        teams = Team.objects.filter(league=brasileirao)
        updated = 0
        for t in teams:
            fixed_id = None
            # Tentar match exato no nome
            if t.name in mapeamento:
                fixed_id = mapeamento[t.name]
            else:
                # Tentar match parcial
                for name_key, sofa_id in mapeamento.items():
                    if name_key in t.name:
                        fixed_id = sofa_id
                        break
            
            if fixed_id:
                # Verificar se o ID já está em uso por outro time (evitar Duplicate Entry)
                conflict = Team.objects.filter(api_id=fixed_id).exclude(id=t.id).first()
                if conflict:
                    print(f" !! Conflito em {fixed_id}: Limpando ID de {conflict.name}")
                    conflict.api_id = None
                    conflict.save()
                
                t.api_id = fixed_id
                t.save()
                print(f" ✓ {t.name} -> {t.api_id}")
                updated += 1
            else:
                print(f" ? Time não mapeado: {t.name}")
        
        print(f"\nFinalizado: {updated} times do Brasileirão atualizados.")
    else:
        print(" !! Erro: Liga 'Brasileirão' não encontrada no banco.")

    print("\n=== REPARO CONCLUÍDO. LIMPE O CACHE E RECARREGUE O SITE. ===")

if __name__ == '__main__':
    super_fix()
