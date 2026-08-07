import os
import django
from django.db.models import Count, Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Match, LeagueStanding

def clean_duplicates():
    print("Iniciando limpeza de ligas duplicadas...")
    
    # 1. Encontrar nomes duplicados
    from django.db.models import Count
    duplicates = League.objects.values('name').annotate(name_count=Count('name')).filter(name_count__gt=1)
    
    print(f"Encontrados {duplicates.count()} nomes com duplicatas.")
    
    for item in duplicates:
        name = item['name']
        print(f"\nVerificando duplicatas para: {name}")
        
        # Buscar todas as ligas com esse nome
        leagues = League.objects.filter(name=name).annotate(
            num_matches=Count('matches', distinct=True), 
            num_standings=Count('standings', distinct=True)
        )
        
        # Ordenar (quem tem mais dados fica em primeiro)
        # Critério: Soma de Matches + Standings
        # Se empate, o ID mais recente (maior) ganha? Ou o mais antigo? 
        # Geralmente o que já existe (ID menor) é o original, mas aqui o user disse que baixou dados novos.
        # Vamos assumir que "ter dados" é o critério ouro.
        
        sorted_leagues = sorted(leagues, key=lambda x: (x.num_matches + x.num_standings, x.id), reverse=True)
        
        # O primeiro da lista é o "Vencedor"
        winner = sorted_leagues[0]
        losers = sorted_leagues[1:]
        
        print(f" -> Manter: ID {winner.id} ({winner.country}) - Matches: {winner.num_matches}, Standings: {winner.num_standings}")
        
        for loser in losers:
            # Check de segurança: Só deletar se tiver MUITO menos dados ou zero
            winner_score = winner.num_matches + winner.num_standings
            loser_score = loser.num_matches + loser.num_standings
            
            if loser_score > 0 and loser_score > (winner_score * 0.5):
                print(f" [ALERTA] ID {loser.id} tem dados relevantes ({loser_score}). NÃO vou deletar automaticamente por segurança.")
            else:
                print(f" -> DELETANDO: ID {loser.id} ({loser.country}) - Vazio ou quase vazio.")
                loser.delete()

if __name__ == '__main__':
    clean_duplicates()
