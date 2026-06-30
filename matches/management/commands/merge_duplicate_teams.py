from django.core.management.base import BaseCommand
from matches.models import Match, Team, League
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Mescla jogos de times duplicados (ex: da Serie A) para os times oficiais do Brasileirao'

    def handle(self, *args, **options):
        brasileirao = League.objects.filter(name__iexact='Brasileirão').first()
        if not brasileirao:
            self.stdout.write("Liga Brasileirão não encontrada.")
            return

        # Pega todos os times do Brasileirao
        times_oficiais = Team.objects.filter(league=brasileirao)
        
        for time_oficial in times_oficiais:
            # Encontra times com o MESMO NOME em outras ligas (ex: Serie A)
            duplicados = Team.objects.filter(name__iexact=time_oficial.name).exclude(league=brasileirao)
            
            for dup in duplicados:
                count_home_moved = 0
                count_away_moved = 0
                count_deleted = 0
                
                # 1. Move os jogos como mandante, um a um para tratar erros
                for match in Match.objects.filter(home_team=dup):
                    match.home_team = time_oficial
                    try:
                        match.save(update_fields=['home_team'])
                        count_home_moved += 1
                    except IntegrityError:
                        # Jogo duplicado já existe para o time oficial! Deletamos a duplicata.
                        match.delete()
                        count_deleted += 1
                
                # 2. Move os jogos como visitante
                for match in Match.objects.filter(away_team=dup):
                    match.away_team = time_oficial
                    try:
                        match.save(update_fields=['away_team'])
                        count_away_moved += 1
                    except IntegrityError:
                        match.delete()
                        count_deleted += 1
                
                if count_home_moved > 0 or count_away_moved > 0 or count_deleted > 0:
                    self.stdout.write(self.style.SUCCESS(
                        f"✅ {time_oficial.name}: Movidos {count_home_moved} em casa, {count_away_moved} fora. {count_deleted} duplicatas deletadas."
                    ))
                
                # 3. Transfere o API ID se o oficial estiver sem, e o duplicado tiver
                if not time_oficial.api_id and dup.api_id:
                    time_oficial.api_id = dup.api_id
                    time_oficial.save(update_fields=['api_id'])
                    self.stdout.write(f"  -> API ID {dup.api_id} copiado para o oficial.")

        # Tratamento especial para o "Athletico" (nome diferente)
        athletico_pr = Team.objects.filter(league=brasileirao, name__iexact='Athletico-PR').first()
        athletico_falso = Team.objects.filter(league=brasileirao, name__iexact='Athletico').first()
        
        if athletico_pr and athletico_falso:
            ch, ca, cd = 0, 0, 0
            for match in Match.objects.filter(home_team=athletico_falso):
                match.home_team = athletico_pr
                try:
                    match.save(update_fields=['home_team'])
                    ch += 1
                except IntegrityError:
                    match.delete()
                    cd += 1
                    
            for match in Match.objects.filter(away_team=athletico_falso):
                match.away_team = athletico_pr
                try:
                    match.save(update_fields=['away_team'])
                    ca += 1
                except IntegrityError:
                    match.delete()
                    cd += 1
            
            if ch > 0 or ca > 0 or cd > 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Movidos {ch} home, {ca} away do 'Athletico'. {cd} deletados."))
            
            athletico_falso.delete()
            self.stdout.write("🗑️ Time 'Athletico' deletado com sucesso.")

        self.stdout.write(self.style.SUCCESS("\n🎉 Mesclagem concluída! Os gráficos no site devem estar 100% preenchidos agora."))
