from django.core.management.base import BaseCommand
from django.db.models import Count
from matches.models import Match

class Command(BaseCommand):
    help = "Remove jogos duplicados (mesma temporada, mandante e visitante)"

    def handle(self, *args, **options):
        # Passo 1: Remover jogos sem mandante ou visitante (dados corrompidos)
        Match.objects.filter(home_team__isnull=True).delete()
        Match.objects.filter(away_team__isnull=True).delete()

        # Passo 2: Duplicatas estritas (mesma data, mesmo home, mesmo away)
        # Isso corrige importações múltiplas do mesmo jogo exato
        duplicates_strict = (
            Match.objects.values('date', 'home_team', 'away_team')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        
        count_strict = 0
        total_items = duplicates_strict.count()
        self.stdout.write(f"Encontrados {total_items} grupos de duplicatas exatas (data/home/away).")

        for i, item in enumerate(duplicates_strict):
            if i % 100 == 0:
                self.stdout.write(f"Processando grupo {i}/{total_items}...")
            matches = Match.objects.filter(
                date=item['date'],
                home_team=item['home_team'],
                away_team=item['away_team']
            ).order_by('-api_id', '-id') # Prioriza quem tem API ID e ID mais alto
            
            # Mantém o primeiro, deleta o resto
            for m in matches[1:]:
                m.delete()
                count_strict += 1
                
        self.stdout.write(f"Removidas {count_strict} duplicatas exatas.")

        # Passo 3: Duplicatas lógicas (mesma temporada, mandante e visitante)
        # Isso garante que times joguem apenas UMA vez com mando de campo por temporada
        duplicates = (
            Match.objects.values('season', 'home_team', 'away_team')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        total_groups = duplicates.count()
        total_deleted = 0
        
        self.stdout.write(f"Encontrados {total_groups} confrontos duplicados (mesma temporada/mandante/visitante).")

        for item in duplicates:
            matches = Match.objects.filter(
                season=item['season'],
                home_team=item['home_team'],
                away_team=item['away_team']
            )
            
            # Critério de desempate para manter o "melhor" jogo:
            # 1. Tem API ID (veio da API paga/oficial)
            # 2. Tem status 'Finished'
            # 3. Tem placar (home_score não é nulo)
            # 4. Data mais recente (assumindo correção)
            # 5. ID maior (último inserido)
            
            sorted_matches = sorted(matches, key=lambda m: (
                1 if m.api_id else 0,
                1 if m.status == 'Finished' else 0,
                1 if m.home_score is not None else 0,
                m.date,
                m.id
            ), reverse=True)
            
            keep = sorted_matches[0]
            delete_list = sorted_matches[1:]
            
            for m in delete_list:
                self.stdout.write(f"Removendo duplicata: {m.home_team} vs {m.away_team} ({m.date}) [ID: {m.id}]")
                m.delete()
                total_deleted += 1
                
        self.stdout.write(self.style.SUCCESS(f"Limpeza concluída. Removidos {total_deleted} jogos duplicados."))
