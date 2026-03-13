import os
import sys
import django  # type: ignore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League  # type: ignore
from django.db import transaction, models  # type: ignore

def final_brand_repair():
    print("=== REPARO DEFINITIVO DE LOGOS E IDS (LOCAL + PROD) ===\n")

    # Mapeamento Real SofaScore (Baseado nos arquivos físicos que temos)
    # Formato: (Nome Parcial, País) -> API_ID Real SofaScore
    mapeamento_real = [
        # --- BRASIL ---
        ("São Paulo", "Brasil", "sofa_1981"),
        ("Palmeiras", "Brasil", "sofa_1963"),
        ("Fluminense", "Brasil", "sofa_1961"),
        ("Grêmio", "Brasil", "sofa_5926"),
        ("Bahia", "Brasil", "sofa_1955"),
        ("Flamengo", "Brasil", "sofa_5981"),
        ("Coritiba", "Brasil", "sofa_1982"),
        ("Athletico", "Brasil", "sofa_1967"),
        ("Corinthians", "Brasil", "sofa_1957"),
        ("Bragantino", "Brasil", "sofa_1999"),
        ("Mirassol", "Brasil", "sofa_21982"),
        ("Chapecoense", "Brasil", "sofa_21845"),
        ("Atletico-MG", "Brasil", "sofa_1977"),
        ("Atlético Mineiro", "Brasil", "sofa_1977"),
        ("Santos", "Brasil", "sofa_1968"),
        ("Vasco", "Brasil", "sofa_1974"),
        ("Vitória", "Brasil", "sofa_1962"),
        ("Botafogo", "Brasil", "sofa_1958"),
        ("Remo", "Brasil", "sofa_2012"),
        ("Internacional", "Brasil", "sofa_1966"),
        ("Cruzeiro", "Brasil", "sofa_1954"),
        ("Americo-MG", "Brasil", "sofa_1973"),
        ("América Mineiro", "Brasil", "sofa_1973"),
        ("America-MG", "Brasil", "sofa_1973"),
        ("Cuiaba", "Brasil", "sofa_49202"),
        ("Ceara", "Brasil", "sofa_2001"),
        ("Fortaleza", "Brasil", "sofa_2020"),
        ("Goias", "Brasil", "sofa_1960"),
        ("Criciuma", "Brasil", "sofa_1984"),
        ("Juventude", "Brasil", "sofa_1980"),
        ("Avai", "Brasil", "sofa_7315"),
        ("Atlético Goianiense", "Brasil", "sofa_7314"),
        ("Sport Recife", "Brasil", "sofa_1959"),

        # --- SUÍÇA (Garantir) ---
        ("Young Boys", "Suica", "sofa_2452"),
        ("Basel", "Suica", "sofa_2443"),
        ("Lugano", "Suica", "sofa_2448"),
        ("Luzern", "Suica", "sofa_2445"),
        ("Sion", "Suica", "sofa_2446"),
        ("St. Gallen", "Suica", "sofa_2450"),
        ("Zürich", "Suica", "sofa_2453"),
        ("Servette", "Suica", "sofa_2454"),
        ("Winterthur", "Suica", "sofa_2458"),
        ("Grasshopper", "Suica", "sofa_2442"),
        ("Lausanne", "Suica", "sofa_2451"),

        # --- BÉLGICA (Garantir) ---
        ("Anderlecht", "Belgica", "sofa_2900"),
        ("Club Brugge", "Belgica", "sofa_2890"),
        ("Antwerp", "Belgica", "sofa_2889"),
        ("Gent", "Belgica", "sofa_2903"),
        ("Genk", "Belgica", "sofa_2895"),
        ("Standard", "Belgica", "sofa_2901"),
    ]

    with transaction.atomic():
        print("Limpando conflitos de api_id...")
        all_apis = [m[2] for m in mapeamento_real]
        Team.objects.filter(api_id__in=all_apis).update(api_id=None)

        for name_query, country, api_id in mapeamento_real:
            # 1. Tentar busca exata primeiro
            teams = Team.objects.filter(
                name=name_query,
                league__country__icontains=country
            ).distinct()

            # 2. Se não achar exato, tenta conter (mas só se for único)
            if not teams.exists():
                teams = Team.objects.filter(
                    name__icontains=name_query,
                    league__country__icontains=country
                ).distinct()

            if teams.exists():
                # Se ainda houver múltiplos após icontains, pega o primeiro para não quebrar a Unique
                t = teams.first()
                t.api_id = api_id
                t.save()
                print(f"  ✓ {t.name} ({country}) -> {api_id}")
            else:
                print(f"  ✗ Time não encontrado: {name_query} ({country})")

    # Limpar Cache
    from django.core.cache import cache  # type: ignore
    cache.clear()
    print("\n=== REPARO CONCLUÍDO! Logos e IDs sincronizados. ===")

if __name__ == "__main__":
    final_brand_repair()
