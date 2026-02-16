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
        # Tenta encontrar com ou sem acento
        league = League.objects.filter(name=league_name).first()
        if not league:
            league = League.objects.filter(name="Brasileirao").first()
        
        if not league:
            self.stdout.write(self.style.ERROR(f"Liga {league_name} (ou sem acento) não encontrada."))
            return

        self.stdout.write(f"Iniciando deduplicação para a liga: {league.name} (ID: {league.id})")

        with transaction.atomic():
            # Itera sobre TODOS os times da liga para garantir que pegamos mesmo com espaços extras
            all_teams = Team.objects.filter(league=league)
            
            for team in all_teams:
                # Normaliza o nome do time atual (remove espaços extras)
                clean_name = team.name.strip()
                
                # Verifica se esse nome está na lista de "nomes ruins"
                if clean_name in mappings:
                    good_name = mappings[clean_name]
                    
                    # Se o nome atual já é o nome bom, ignora
                    if clean_name == good_name:
                        continue
                        
                    self.stdout.write(f"Encontrado candidato: '{team.name}' -> deve ser '{good_name}'")

                    # Busca o time "oficial" (destino)
                    good_team = Team.objects.filter(name=good_name, league=league).first()

                    if good_team:
                        if team.id == good_team.id:
                            continue
                            
                        self.stdout.write(f"Mesclando '{team.name}' (ID: {team.id}) -> '{good_team.name}' (ID: {good_team.id})")
                        
                        # Move os jogos
                        updated_home = Match.objects.filter(home_team=team).update(home_team=good_team)
                        updated_away = Match.objects.filter(away_team=team).update(away_team=good_team)
                        
                        self.stdout.write(f"  - Jogos movidos: {updated_home} (Casa) + {updated_away} (Fora)")
                        
                        # Apaga o time duplicado
                        team.delete()
                    else:
                        # Se o time oficial não existe, apenas renomeia este
                        self.stdout.write(f"Renomeando '{team.name}' -> '{good_name}'")
                        team.name = good_name
                        team.save()

        self.stdout.write(self.style.SUCCESS("Deduplicação concluída!"))
