import os
import django
import sys
from django.db.models import Count

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import League, Season, LeagueStanding, Match

def final_check():
    try:
        league = League.objects.get(name='Superliga', country='Dinamarca')
        print(f"=== Relatório Final Superliga Dinamarca ===")
        print(f"League ID: {league.id}")
        
        # 1. Standings Check
        print("\n1. Tabela de Classificação (2026):")
        standings_2026 = LeagueStanding.objects.filter(league=league, season__year=2026).order_by('position')
        if standings_2026.exists():
            print(f"{'Pos':<4} {'Time':<20} {'J':<4} {'Pts':<4}")
            for s in standings_2026:
                print(f"{s.position:<4} {s.team.name:<20} {s.played:<4} {s.points:<4}")
        else:
            print("ERRO: Tabela 2026 não encontrada.")

        # 2. Match Count Check
        print("\n2. Contagem de Jogos (2026):")
        matches_2026 = Match.objects.filter(league=league, season__year=2026)
        total = matches_2026.count()
        finished = matches_2026.filter(status__in=['Finished', 'FT', 'AET', 'PEN', 'FINISHED']).count()
        print(f"Total de jogos: {total}")
        print(f"Jogos finalizados: {finished}")
        
        # 3. May Matches Check
        print("\n3. Verificação de Jogos em Maio (Temporada 2026):")
        may_matches = matches_2026.filter(date__month=5)
        if may_matches.exists():
            print(f"ALERTA: Encontrados {may_matches.count()} jogos em Maio!")
        else:
            print("OK: Nenhum jogo em Maio encontrado para a temporada 2026.")

        # 4. Duplicates Check
        print("\n4. Verificação de Duplicatas (Data + Times):")
        # Reuse logic from check_match_duplicates_detailed.py
        from collections import Counter
        all_matches = Match.objects.filter(league=league)
        sigs = [(m.date.strftime('%Y-%m-%d') if m.date else "No Date", m.home_team.name, m.away_team.name) for m in all_matches]
        counts = Counter(sigs)
        dups = {k: v for k, v in counts.items() if v > 1}
        if dups:
            print(f"ALERTA: Encontradas {len(dups)} duplicatas.")
        else:
            print("OK: Nenhuma duplicata encontrada.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    final_check()
