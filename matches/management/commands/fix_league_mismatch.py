from django.core.management.base import BaseCommand
from matches.models import Match, Team, League
from django.db import models, IntegrityError

class Command(BaseCommand):
    help = 'Corrige os jogos que foram mesclados de forma errada para outras ligas, e deleta os que são inválidos'

    def handle(self, *args, **options):
        # 1. Corrige ou deleta mandantes inválidos
        matches = Match.objects.exclude(home_team__league=models.F('league'))
        
        count_fixed_home = 0
        count_deleted_home = 0
        
        for m in list(matches):
            correct_home_team = Team.objects.filter(league=m.league, name__iexact=m.home_team.name).first()
            if correct_home_team:
                m.home_team = correct_home_team
                try:
                    m.save(update_fields=['home_team'])
                    count_fixed_home += 1
                except IntegrityError:
                    m.delete()
                    count_deleted_home += 1
            else:
                # Se não há time com esse nome na liga da partida, a partida é inválida (ex: time da Série B no Brasileirão)
                m.delete()
                count_deleted_home += 1
                
        # 2. Corrige ou deleta visitantes inválidos
        matches_away = Match.objects.exclude(away_team__league=models.F('league'))
        count_fixed_away = 0
        count_deleted_away = 0
        
        for m in list(matches_away):
            correct_away_team = Team.objects.filter(league=m.league, name__iexact=m.away_team.name).first()
            if correct_away_team:
                m.away_team = correct_away_team
                try:
                    m.save(update_fields=['away_team'])
                    count_fixed_away += 1
                except IntegrityError:
                    m.delete()
                    count_deleted_away += 1
            else:
                m.delete()
                count_deleted_away += 1
                
        self.stdout.write(self.style.SUCCESS(
            f"✅ Limpeza concluída! \n"
            f"Mandantes: {count_fixed_home} corrigidos, {count_deleted_home} deletados (inválidos/duplicados).\n"
            f"Visitantes: {count_fixed_away} corrigidos, {count_deleted_away} deletados (inválidos/duplicados)."
        ))

        # Para o Athletic Club na Série B
        serie_b = League.objects.filter(name__icontains='Série B').first()
        if serie_b:
            athletic_club = Team.objects.filter(league=serie_b, name__iexact='Athletic Club').first()
            athletico_pr = Team.objects.filter(league__name__iexact='Brasileirão', name__iexact='Athletico-PR').first()
            
            if athletic_club and athletico_pr:
                c_h, c_a, c_d = 0, 0, 0
                for match in Match.objects.filter(league=serie_b, home_team=athletico_pr):
                    match.home_team = athletic_club
                    try:
                        match.save(update_fields=['home_team'])
                        c_h += 1
                    except IntegrityError:
                        match.delete()
                        c_d += 1
                
                for match in Match.objects.filter(league=serie_b, away_team=athletico_pr):
                    match.away_team = athletic_club
                    try:
                        match.save(update_fields=['away_team'])
                        c_a += 1
                    except IntegrityError:
                        match.delete()
                        c_d += 1
                
                if c_h > 0 or c_a > 0 or c_d > 0:
                    self.stdout.write(self.style.SUCCESS(f"✅ Revertidos jogos do Athletic Club na Série B: {c_h} mandante, {c_a} visitante, {c_d} deletados."))
