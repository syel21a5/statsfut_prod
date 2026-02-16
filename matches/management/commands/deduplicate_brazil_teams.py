from django.core.management.base import BaseCommand
from django.db import transaction
from matches.models import Team, Match, League
from matches.utils import TEAM_NAME_MAPPINGS

class Command(BaseCommand):
    help = "Remove duplicatas de times brasileiros unificando os registros"

    def handle(self, *args, **options):
        # Mapeamento (Nome Incorreto -> Nome Correto)
        # Importado de utils.py
        mappings = TEAM_NAME_MAPPINGS

        league_name = "Brasileirão"
        league = League.objects.filter(name=league_name).first()
        
        if not league:
            self.stdout.write(self.style.ERROR(f"Liga {league_name} não encontrada."))
            return

        self.stdout.write(f"Iniciando deduplicação para {league_name}...")

        with transaction.atomic():
            for bad_name, good_name in mappings.items():
                # Tenta buscar o time "errado"
                bad_team = Team.objects.filter(name=bad_name, league=league).first()
                if not bad_team:
                    continue

                # Tenta buscar o time "certo"
                good_team = Team.objects.filter(name=good_name, league=league).first()

                if good_team:
                    if bad_team.id == good_team.id:
                        continue
                        
                    self.stdout.write(f"Mesclando '{bad_name}' (ID: {bad_team.id}) -> '{good_name}' (ID: {good_team.id})")
                    
                    # Atualiza jogos onde o time ruim era mandante
                    updated_home = Match.objects.filter(home_team=bad_team).update(home_team=good_team)
                    
                    # Atualiza jogos onde o time ruim era visitante
                    updated_away = Match.objects.filter(away_team=bad_team).update(away_team=good_team)
                    
                    self.stdout.write(f"  - Jogos movidos: {updated_home} (Casa) + {updated_away} (Fora)")
                    
                    # Apaga o time duplicado
                    bad_team.delete()
                else:
                    self.stdout.write(f"Renomeando '{bad_name}' -> '{good_name}'")
                    bad_team.name = good_name
                    bad_team.save()

        self.stdout.write(self.style.SUCCESS("Deduplicação concluída!"))
