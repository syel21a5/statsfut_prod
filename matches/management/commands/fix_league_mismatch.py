from django.core.management.base import BaseCommand
from matches.models import Match, Team, League
from django.db import models

class Command(BaseCommand):
    help = 'Corrige os jogos que foram mesclados de forma errada para outras ligas'

    def handle(self, *args, **options):
        # Encontra jogos onde o time da casa NÃO pertence à mesma liga do jogo
        matches = Match.objects.exclude(home_team__league=models.F('league'))
        
        count_fixed_home = 0
        count_fixed_away = 0
        
        for m in matches:
            # Precisa voltar o home_team para o time do mesmo NOME que está na liga do jogo
            correct_home_team = Team.objects.filter(league=m.league, name__iexact=m.home_team.name).first()
            if correct_home_team:
                m.home_team = correct_home_team
                m.save(update_fields=['home_team'])
                count_fixed_home += 1
                
        # O mesmo para o time de fora
        matches_away = Match.objects.exclude(away_team__league=models.F('league'))
        for m in matches_away:
            correct_away_team = Team.objects.filter(league=m.league, name__iexact=m.away_team.name).first()
            if correct_away_team:
                m.away_team = correct_away_team
                m.save(update_fields=['away_team'])
                count_fixed_away += 1
                
        self.stdout.write(self.style.SUCCESS(f"✅ Revertido com sucesso! Corrigidos {count_fixed_home} mandantes e {count_fixed_away} visitantes."))

        # Para o Athletico (que foi renomeado e o original deletado)
        # O Athletico da Série B virou "Athletic Club", então jogos dele que foram para "Athletico-PR" (Brasileirão)
        # E que o jogo seja da Série B, precisamos voltar pro Athletic Club
        serie_b = League.objects.filter(name__icontains='Série B').first()
        if serie_b:
            athletic_club = Team.objects.filter(league=serie_b, name__iexact='Athletic Club').first()
            athletico_pr = Team.objects.filter(league__name__iexact='Brasileirão', name__iexact='Athletico-PR').first()
            
            if athletic_club and athletico_pr:
                # Se algum jogo da Serie B ainda estiver apontando para o Athletico-PR
                m_h = Match.objects.filter(league=serie_b, home_team=athletico_pr)
                c_h = m_h.count()
                m_h.update(home_team=athletic_club)
                
                m_a = Match.objects.filter(league=serie_b, away_team=athletico_pr)
                c_a = m_a.count()
                m_a.update(away_team=athletic_club)
                
                if c_h > 0 or c_a > 0:
                    self.stdout.write(self.style.SUCCESS(f"✅ Revertidos {c_h} mandantes e {c_a} visitantes do Athletic Club."))
