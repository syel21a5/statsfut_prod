import os
import sys
import django  # type: ignore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, LeagueStanding  # type: ignore
from django.db import transaction, models  # type: ignore

def repair_by_name():
    print("=== REPARO UNIVERSAL POR NOME (Agnóstico a IDs) ===\n")

    # Mapeamento: (País, Nome Parcial/Exato) -> API_ID
    mappings = [
        # --- SUÍÇA ---
        ("Suica", "Young Boys", "sofa_2452"),
        ("Suica", "Basel", "sofa_2443"),
        ("Suica", "Lugano", "sofa_2448"),
        ("Suica", "Luzern", "sofa_2445"),
        ("Suica", "Sion", "sofa_2446"),
        ("Suica", "St. Gallen", "sofa_2450"),
        ("Suica", "Zürich", "sofa_2453"),
        ("Suica", "Zurich", "sofa_2453"),
        ("Suica", "Servette", "sofa_2454"),
        ("Suica", "Winterthur", "sofa_2458"),
        ("Suica", "Grasshopper", "sofa_2442"),
        ("Suica", "Lausanne-Sport", "sofa_2451"),
        ("Suica", "Lausanne", "sofa_2451"),
        ("Suica", "Thun", "sofa_2449"),
        ("Suica", "Yverdon", "sofa_2501"),
        ("Suica", "Vaduz", "sofa_2463"),
        ("Suica", "Stade-Lausanne-Ouchy", "sofa_35162"),
        ("Suica", "Xamax", "sofa_2447"),

        # --- BÉLGICA ---
        ("Belgica", "Anderlecht", "sofa_2900"),
        ("Belgica", "Antwerp", "sofa_2889"),
        ("Belgica", "Cercle Brugge", "sofa_2888"),
        ("Belgica", "Club Brugge", "sofa_2890"),
        ("Belgica", "Charleroi", "sofa_2898"),
        ("Belgica", "Gent", "sofa_2903"),
        ("Belgica", "Genk", "sofa_2895"),
        ("Belgica", "Mechelen", "sofa_2901"),
        ("Belgica", "Leuven", "sofa_116075"),
        ("Belgica", "Sint-Truiden", "sofa_2893"),
        ("Belgica", "Standard", "sofa_2887"),
        ("Belgica", "Westerlo", "sofa_2926"),
        ("Belgica", "Zulte", "sofa_2933"),
        ("Belgica", "Dender", "sofa_5044"),
        ("Belgica", "Beerschot", "sofa_169260"),
        ("Belgica", "Union Saint-Gilloise", "sofa_4860"),
        ("Belgica", "Kortrijk", "sofa_4858"),

        # --- BRASIL ---
        ("Brasil", "América", "sofa_1973"),
        ("Brasil", "Athletico", "sofa_1967"),
        ("Brasil", "Atlético Goianiense", "sofa_7314"),
        ("Brasil", "Atlético Mineiro", "sofa_1977"),
        ("Brasil", "Avai", "sofa_7315"),
        ("Brasil", "Bahia", "sofa_1955"),
        ("Brasil", "Botafogo", "sofa_1958"),
        ("Brasil", "Ceara", "sofa_2001"),
        ("Brasil", "Chapecoense", "sofa_21845"),
        ("Brasil", "Corinthians", "sofa_1957"),
        ("Brasil", "Coritiba", "sofa_1982"),
        ("Brasil", "Criciuma", "sofa_1984"),
        ("Brasil", "Cruzeiro", "sofa_1954"),
        ("Brasil", "Cuiaba", "sofa_49202"),
        ("Brasil", "Flamengo", "sofa_5981"),
        ("Brasil", "Fluminense", "sofa_1961"),
        ("Brasil", "Fortaleza", "sofa_2020"),
        ("Brasil", "Goias", "sofa_1960"),
        ("Brasil", "Grêmio", "sofa_5926"),
        ("Brasil", "Internacional", "sofa_1966"),
        ("Brasil", "Juventude", "sofa_1980"),
        ("Brasil", "Mirassol", "sofa_21982"),
        ("Brasil", "Palmeiras", "sofa_1963"),
        ("Brasil", "Bragantino", "sofa_1999"),
        ("Brasil", "Remo", "sofa_2012"),
        ("Brasil", "Santos", "sofa_1968"),
        ("Brasil", "São Paulo", "sofa_1981"),
        ("Brasil", "Sport", "sofa_1959"),
        ("Brasil", "Vasco", "sofa_1974"),
        ("Brasil", "Vitória", "sofa_1962"),
    ]

    with transaction.atomic():
        # PASSO 1: Limpar api_id de todos os times que podem conflitar
        all_apis = [m[2] for m in mappings]
        cleared = Team.objects.filter(api_id__in=all_apis).update(api_id=None)
        print(f"Limpando {cleared} api_ids pré-existentes para evitar conflitos de Unique.\n")

        # PASSO 2: Aplicar mapeamento por nome
        for country, name_query, api_id in mappings:
            # Tenta encontrar o time pelo nome e país
            # Filtramos por país para evitar conflitos (ex: "Vasco" no Brasil)
            teams = Team.objects.filter(
                models.Q(name__icontains=name_query),
                models.Q(league__country__icontains=country)
            ).distinct()

            if teams.count() == 0:
                print(f"  [AVISO] Time não encontrado: {name_query} ({country})")
            elif teams.count() > 1:
                # Se houver mais de um, pega o que tem nome mais parecido ou o primeiro
                target = teams.first()
                print(f"  [NOTAS] Múltiplos times para '{name_query}' ({country}). Usando ID {target.id}: {target.name}")
                target.api_id = api_id
                target.save()
            else:
                target = teams.first()
                target.api_id = api_id
                target.save()
                print(f"  ✓ {target.name} ({country}) → {api_id}")

    print("\n--- Limpando Cache ---")
    from django.core.cache import cache  # type: ignore
    cache.clear()
    print("\n=== REPARO CONCLUÍDO! IDs baseados em nomes aplicados com sucesso. ===")

if __name__ == "__main__":
    repair_by_name()
