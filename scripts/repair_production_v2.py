import os
import sys
import django  # type: ignore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, LeagueStanding  # type: ignore
from django.core.management import call_command  # type: ignore
from django.db import transaction  # type: ignore

def repair():
    print("=== REPARO CIRÚRGICO DA PRODUÇÃO (v2) ===\n")

    # =========================================================================
    # 1. SUÍÇA: Definir api_ids usando IDs exatos do banco de produção
    #    Nomes no banco: Young Boys, Grasshoppers, Lausanne, Lugano, etc.
    # =========================================================================
    print("--- [1/5] Suíça: Definindo API IDs ---")
    swiss_team_ids = {
        1972: "sofa_2452",  # Young Boys
        1971: "sofa_2443",  # Basel
        1976: "sofa_2448",  # Lugano
        1969: "sofa_2445",  # Luzern
        1967: "sofa_2446",  # Sion
        1970: "sofa_2450",  # St. Gallen
        1966: "sofa_2453",  # Zurich
        1973: "sofa_2454",  # Servette
        1975: "sofa_2463",  # Winterthur
        1968: "sofa_2442",  # Grasshoppers
        1974: "sofa_2451",  # Lausanne
        1977: "sofa_2449",  # Thun
        2018: "sofa_2501",  # Yverdon
    }

    with transaction.atomic():
        for team_id, api_id in swiss_team_ids.items():
            try:
                team = Team.objects.get(id=team_id)
                team.api_id = api_id
                team.save()
                print(f"  ✓ {team.name} ({team_id}) → {api_id}")
            except Team.DoesNotExist:
                print(f"  SKIP: Time ID {team_id} não encontrado")

    # =========================================================================
    # 2. BÉLGICA: Merge times antigos → novos SofaScore (com api_id)
    #    Transfere todos os jogos do antigo para o novo e deleta o antigo
    # =========================================================================
    print("\n--- [2/5] Bélgica: Unificando duplicatas ---")
    belgium_merges = [
        # (antigo_id, novo_id),  # antigo_nome → novo_nome (com api_id)
        (1871, 2504),  # Club Brugge → Club Brugge KV (sofa_2890)
        (1861, 2516),  # Dender → FCV Dender (sofa_5044)
        (1870, 2512),  # Charleroi → RC Sporting Charleroi (sofa_2889)
        (1874, 2508),  # Gent → KAA Gent (sofa_2898)
        (1952, 2094),  # Kortrijk → KV Kortrijk (sofa_2933)
        (1873, 2505),  # Sint-Truiden → Sint-Truidense VV (sofa_2903)
        (1868, 2510),  # Westerlo → KVC Westerlo (sofa_2926)
        (1863, 2513),  # Zulte-Waregem → SV Zulte Waregem (sofa_2929)
        (1865, 2515),  # La Louviere → RAAL La Louvière (sofa_44019)
        (1860, 2503),  # Royale Union SG → Royale Union Saint-Gilloise (sofa_368506)
    ]

    with transaction.atomic():
        for old_id, new_id in belgium_merges:
            try:
                old_team = Team.objects.get(id=old_id)
                new_team = Team.objects.get(id=new_id)
                home_cnt = Match.objects.filter(home_team=old_team).update(home_team=new_team)
                away_cnt = Match.objects.filter(away_team=old_team).update(away_team=new_team)
                LeagueStanding.objects.filter(team=old_team).delete()
                old_team.delete()
                print(f"  ✓ {old_id}→{new_id}: movido {home_cnt}+{away_cnt} jogos, deletado {old_id}")
            except Team.DoesNotExist:
                print(f"  SKIP: {old_id} ou {new_id} não encontrado")

    # =========================================================================
    # 3. BÉLGICA: Times que já têm histórico consolidado mas sem api_id
    #    (RSC Anderlecht/Antwerp/Mechelen/Genk/OH Leuven foram merged into antigos)
    # =========================================================================
    print("\n--- [3/5] Bélgica: Definindo API IDs dos times consolidados ---")
    belgium_set_api = {
        1867: ("RSC Anderlecht",          "sofa_2887"),
        1859: ("Royal Antwerp FC",        "sofa_2893"),
        1864: ("KV Mechelen",             "sofa_2900"),
        1872: ("KRC Genk",                "sofa_2895"),
        1869: ("Oud-Heverlee Leuven",     "sofa_116075"),
        1862: ("Cercle Brugge",           "sofa_2888"),
    }

    with transaction.atomic():
        for team_id, (new_name, api_id) in belgium_set_api.items():
            try:
                team = Team.objects.get(id=team_id)
                team.name = new_name
                team.api_id = api_id
                team.save()
                print(f"  ✓ {team_id} → '{new_name}' / {api_id}")
            except Team.DoesNotExist:
                print(f"  SKIP: Time ID {team_id} não encontrado")

    # =========================================================================
    # 4. BRASIL: Atualizar api_ids antigos (formato numérico → sofa_xx)
    #    e corrigir nomes com acento
    # =========================================================================
    print("\n--- [4/5] Brasil: Atualizando API IDs e nomes ---")

    # Merge: Athletico-PR (743, histórico) → Athletico (2495, sofa_1967)
    print("  Merging Athletico-PR → Athletico...")
    with transaction.atomic():
        try:
            old = Team.objects.get(id=743)
            new = Team.objects.get(id=2495)
            Match.objects.filter(home_team=old).update(home_team=new)
            Match.objects.filter(away_team=old).update(away_team=new)
            LeagueStanding.objects.filter(team=old).delete()
            old.delete()
            print("    ✓ Athletico-PR (743) consolidado em Athletico (2495)")
        except Team.DoesNotExist:
            print("    SKIP: Athletico-PR ou Athletico não encontrado")

    # Formato: id: (nome_novo_ou_None, api_id)
    brazil_fixes = {
        738: ("Atlético Mineiro", "sofa_1977"),
        737: (None,               "sofa_1963"),  # Palmeiras
        748: (None,               "sofa_5981"),  # Flamengo
        755: (None,               "sofa_1958"),  # Botafogo
        768: (None,               "sofa_1984"),  # Criciuma
        767: (None,               "sofa_1980"),  # Juventude
        744: (None,               "sofa_1966"),  # Internacional
        759: (None,               "sofa_1955"),  # Bahia
        739: (None,               "sofa_1961"),  # Fluminense
        764: (None,               "sofa_2020"),  # Fortaleza
        766: (None,               "sofa_49202"), # Cuiaba
        746: (None,               "sofa_1957"),  # Corinthians
        741: ("Grêmio",           "sofa_5926"),
        745: (None,               "sofa_1954"),  # Cruzeiro
        757: ("Vitória",          "sofa_1962"),
        752: (None,               "sofa_1968"),  # Santos
        761: (None,               "sofa_2001"),  # Ceara
        754: (None,               "sofa_1960"),  # Goias
        735: (None,               "sofa_21845"), # Chapecoense
        749: (None,               "sofa_1959"),  # Sport Recife
        742: (None,               "sofa_1969"),  # Ponte Preta
        756: (None,               "sofa_1976"),  # Santa Cruz
        747: ("São Paulo",        "sofa_1981"),
        736: (None,               "sofa_1982"),  # Coritiba
        769: (None,               "sofa_21982"), # Mirassol
        770: (None,               "sofa_2012"),  # Remo
        862: ("América Mineiro",  "sofa_1973"),
        760: ("Atlético Goianiense", "sofa_7314"),
        765: ("Red Bull Bragantino", "sofa_1999"),
        753: (None,               "sofa_1974"),  # Vasco
        751: (None,               "sofa_7315"),  # Avai
    }

    with transaction.atomic():
        for team_id, (new_name, api_id) in brazil_fixes.items():
            try:
                team = Team.objects.get(id=team_id)
                if new_name:
                    team.name = new_name
                team.api_id = api_id
                team.save()
                print(f"  ✓ {team.name} ({team_id}) → {api_id}")
            except Team.DoesNotExist:
                print(f"  SKIP: Time ID {team_id} não encontrado")

    # =========================================================================
    # 5. BRASIL: Deletar times "lixo" (Home, Away, Points, etc.)
    # =========================================================================
    print("\n--- [5/5] Brasil: Limpando registros inválidos ---")
    junk_ids = [1112, 1109, 1130, 1156, 1110, 1162, 1108, 1111, 1128, 1154, 1116, 1121]
    with transaction.atomic():
        for jid in junk_ids:
            try:
                team = Team.objects.get(id=jid)
                name = team.name
                team.delete()
                print(f"  🗑️  Deletado: '{name}' (ID {jid})")
            except Team.DoesNotExist:
                pass  # Já deletado, OK

    # =========================================================================
    # Final: Recalcular tabelas e limpar cache
    # =========================================================================
    print("\n--- Recalculando classificações ---")
    call_command('recalculate_standings', all=True, smart=False)

    print("\n--- Limpando cache ---")
    from django.core.cache import cache  # type: ignore
    cache.clear()

    print("\n=== CONCLUÍDO! Logos e tabelas devem estar perfeitas agora. ===")

if __name__ == "__main__":
    repair()
