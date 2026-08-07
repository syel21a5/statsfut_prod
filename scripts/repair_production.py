import os
import sys
import django  # type: ignore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League, Match  # type: ignore
from django.core.management import call_command  # type: ignore
from django.db import transaction  # type: ignore

def repair_database():
    print("=== INICIANDO REPARO DO BANCO DE DADOS DE PRODUÇÃO ===")

    # 1. Mapeamento de Correção de Nomes e API IDs (DB Name -> Sofa Name)
    mappings = {
        # SUIÇA
        "Suica": {
            "Young Boys": "BSC Young Boys",
            "Basel": "Basel",
            "Lugano": "FC Lugano",
            "Luzern": "FC Luzern",
            "Sion": "FC Sion",
            "St. Gallen": "FC St. Gallen 1879",
            "Zurich": "FC Zürich",
            "Servette": "Servette FC",
            "Winterthur": "FC Winterthur",
            "Grasshoppers": "Grasshopper Club Zürich",
            "Lausanne": "FC Lausanne-Sport",
            "Thun": "FC Thun",
            "Yverdon": "Yverdon-Sport",
        },
        # BÉLGICA
        "Belgica": {
            "Anderlecht": "RSC Anderlecht",
            "Antwerp": "Royal Antwerp FC",
            "Cercle Brugge": "Cercle Brugge",
            "Charleroi": "RC Sporting Charleroi",
            "Club Brugge": "Club Brugge KV",
            "Dender": "FCV Dender",
            "Genk": "KRC Genk",
            "Gent": "KAA Gent",
            "La Louviere": "RAAL La Louvière",
            "RAAL La Louvi?re": "RAAL La Louvière",
            "Mechelen": "KV Mechelen",
            "OH Leuven": "Oud-Heverlee Leuven",
            "Royale Union SG": "Royale Union Saint-Gilloise",
            "Sint-Truiden": "Sint-Truidense VV",
            "Standard Liege": "Standard Liège",
            "Standard Li?ge": "Standard Liège",
            "Westerlo": "KVC Westerlo",
            "Zulte-Waregem": "SV Zulte Waregem",
            "Kortrijk": "KV Kortrijk",
            "Beerschot": "Beerschot VA",
        },
        # BRASIL
        "Brasil": {
            "Athletico-PR": "Athletico",
            "Botafogo-RJ": "Botafogo",
            "Red Bull Bragantino": "Red Bull Bragantino",
            "Atlético-MG": "Atlético Mineiro",
            "Atletico-MG": "Atlético Mineiro",
            "Grêmio": "Grêmio",
            "Vasco da Gama": "Vasco",
            "Corinthians": "Corinthians",
            "Cruzeiro": "Cruzeiro",
            "Flamengo": "Flamengo",
            "Fluminense": "Fluminense",
            "Palmeiras": "Palmeiras",
            "São Paulo": "São Paulo",
            "Sao Paulo": "São Paulo",
            "Internacional": "Internacional",
            "Juventude": "Juventude",
            "Vitória": "Vitória",
            "Bahia": "Bahia",
            "Fortaleza": "Fortaleza",
            "Mirassol": "Mirassol",
            "Sport Recife": "Sport Recife",
            "Novorizontino": "Novorizontino",
            "Ceara": "Ceará",
            "Santos": "Santos",
        }
    }

    print("\n--- PASSO 1: Padronizando Nomes dos Times ---")
    with transaction.atomic():
        for country_key, name_map in mappings.items():
            for old_name, new_name in name_map.items():
                if old_name != new_name:
                    teams = Team.objects.filter(league__country__icontains=country_key, name=old_name)
                    for team in teams:
                        print(f"Renomeando: '{old_name}' -> '{new_name}' (Liga {team.league.name} ID {team.league_id})")
                        team.name = new_name
                        team.save()

    print("\n--- PASSO 2: Unificando Duplicatas Históricas ---")
    # Isso vai rodar a ferramenta inteligente que funde times com o mesmo nome exato
    call_command('merge_all_historical_duplicates')

    print("\n--- PASSO 3: Associando API IDs Sofascore Baseado no Histórico ---")
    # Forçar os api_ids exatos para garantir as logotipos
    api_ids = {
        # Suíça
        "BSC Young Boys": "sofa_2452",
        "Basel": "sofa_2443",
        "FC Lugano": "sofa_2448",
        "FC Luzern": "sofa_2445",
        "FC Sion": "sofa_2446",
        "FC St. Gallen 1879": "sofa_2450",
        "FC Zürich": "sofa_2453",
        "Servette FC": "sofa_2454",
        "FC Winterthur": "sofa_2463",
        "Grasshopper Club Zürich": "sofa_2442",
        "FC Lausanne-Sport": "sofa_2451",
        "FC Thun": "sofa_2449",
        "Yverdon-Sport": "sofa_2501",
        # Bélgica
        "RSC Anderlecht": "sofa_2887",
        "Royal Antwerp FC": "sofa_2893",
        "Cercle Brugge": "sofa_2888",
        "RC Sporting Charleroi": "sofa_2889",
        "Club Brugge KV": "sofa_2890",
        "FCV Dender": "sofa_5044",
        "KRC Genk": "sofa_2895",
        "KAA Gent": "sofa_2898",
        "RAAL La Louvière": "sofa_44019",
        "KV Mechelen": "sofa_2900",
        "Oud-Heverlee Leuven": "sofa_116075",
        "Royale Union Saint-Gilloise": "sofa_368506",
        "Sint-Truidense VV": "sofa_2903",
        "Standard Liège": "sofa_2918",
        "KVC Westerlo": "sofa_2926",
        "SV Zulte Waregem": "sofa_2929",
        "KV Kortrijk": "sofa_2933",
        "Beerschot VA": "sofa_169260",
        
        # Brasil
        "Palmeiras": "sofa_1963",
        "Flamengo": "sofa_5981",
        "Botafogo": "sofa_1958",
        "Criciuma": "sofa_1984",
        "Juventude": "sofa_1980",
        "Internacional": "sofa_1966",
        "Bahia": "sofa_1955",
        "Fluminense": "sofa_1961",
        "Fortaleza": "sofa_2020",
        "Cuiaba": "sofa_49202",
        "Corinthians": "sofa_1957",
        "Grêmio": "sofa_5926",
        "Cruzeiro": "sofa_1954",
        "Vitória": "sofa_1962",
        "Santos": "sofa_1968",
        "Ceara": "sofa_2001",
        "Goias": "sofa_1960",
        "Avai": "sofa_7315",
        "Chapecoense": "sofa_21845",
        "Sport Recife": "sofa_1959",
        "Figueirense": "sofa_1985",
        "Ponte Preta": "sofa_1969",
        "Vasco da Gama": "sofa_1974",
        "Santa Cruz": "sofa_1976",
        "São Paulo": "sofa_1981",
        "Coritiba": "sofa_1982",
        "Red Bull Bragantino": "sofa_1999",
        "Mirassol": "sofa_21982",
        "Remo": "sofa_2012",
        "Athletico": "sofa_1967",
        "Atlético Mineiro": "sofa_1977",
        "América Mineiro": "sofa_1973",
        "Atlético Goianiense": "sofa_7314",
        "Paraná Clube": "sofa_1965",
        "CSA": "sofa_2010",
    }
    
    with transaction.atomic():
        for t_name, t_api in api_ids.items():
            teams = Team.objects.filter(name=t_name)
            for team in teams:
                # Remove o api_id de qualquer outro time que já o possua
                conflicting_teams = Team.objects.filter(api_id=t_api).exclude(id=team.id)
                for c_team in conflicting_teams:
                    print(f"Removendo API ID '{t_api}' do time '{c_team.name}' (conflito)")
                    c_team.api_id = None
                    c_team.save()

                team.api_id = t_api
                team.save()
                print(f"API ID {t_api} definido para {team.name} (Liga {team.league_id})")

    print("\n--- PASSO 4: Recalculando Classificações (Standings) ---")
    call_command('recalculate_standings', all=True, smart=False) # Recalcula TUDO para garantir 100%

    print("\n--- PASSO 5: Limpando Cache do Servidor ---")
    from django.core.cache import cache  # type: ignore
    cache.clear()

    print("\n=== REPARO CONCLUÍDO COM SUCESSO! ===")
    print("As logotipos e as tabelas devem estar perfeitas na produção agora.")

if __name__ == "__main__":
    repair_database()
