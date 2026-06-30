from django.core.management.base import BaseCommand
from matches.models import Match, Team, League

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
                # 1. Move os jogos como mandante
                matches_home = Match.objects.filter(home_team=dup)
                count_home = matches_home.count()
                matches_home.update(home_team=time_oficial)
                
                # 2. Move os jogos como visitante
                matches_away = Match.objects.filter(away_team=dup)
                count_away = matches_away.count()
                matches_away.update(away_team=time_oficial)
                
                if count_home > 0 or count_away > 0:
                    self.stdout.write(self.style.SUCCESS(
                        f"✅ {time_oficial.name}: Movidos {count_home} jogos em casa e {count_away} fora da liga '{dup.league.name if dup.league else 'N/A'}' para o Brasileirão."
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
            # Move os jogos
            mh = Match.objects.filter(home_team=athletico_falso)
            ch = mh.count()
            mh.update(home_team=athletico_pr)
            
            ma = Match.objects.filter(away_team=athletico_falso)
            ca = ma.count()
            ma.update(away_team=athletico_pr)
            
            if ch > 0 or ca > 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Movidos {ch} home e {ca} away do 'Athletico' para 'Athletico-PR'"))
            
            # Deleta o falso
            athletico_falso.delete()
            self.stdout.write("🗑️ Time 'Athletico' deletado com sucesso.")

        self.stdout.write(self.style.SUCCESS("\n🎉 Mesclagem concluída! Os gráficos no site devem estar 100% preenchidos agora."))
