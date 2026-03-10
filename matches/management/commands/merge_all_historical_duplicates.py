from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, LeagueStanding
from matches.utils import normalize_team_name
from django.db import transaction

class Command(BaseCommand):
    help = "Unifica times duplicados em todas as ligas usando o TEAM_NAME_MAPPINGS do utils.py"

    def handle(self, *args, **options):
        self.stdout.write("Iniciando limpeza massiva de times duplicados...")
        
        leagues = League.objects.all()
        total_merged = 0

        for league in leagues:
            teams = Team.objects.filter(league=league)
            # Dicionário para rastrear o time 'correto' (canônico)
            # canonical_name -> Team object
            canonical_teams = {}
            
            for team in teams:
                c_name = normalize_team_name(team.name)
                
                if c_name not in canonical_teams:
                    canonical_teams[c_name] = team
                else:
                    # Encontramos uma duplicata!
                    target_team = canonical_teams[c_name]
                    if team.id != target_team.id:
                        self.stdout.write(f"Unificando '{team.name}' (ID {team.id}) -> '{target_team.name}' (ID {target_team.id}) em {league.name}")
                        self.merge_teams(team, target_team)
                        total_merged += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Limpeza concluída! Total de merges realizados: {total_merged}"))
        self.stdout.write(self.style.WARNING("Dica: Rode 'python manage.py recalculate_standings --all --smart' agora."))

    @transaction.atomic
    def merge_teams(self, source_team, target_team):
        # 1. Atualizar jogos (casa)
        Match.objects.filter(home_team=source_team).update(home_team=target_team)
        
        # 2. Atualizar jogos (fora)
        Match.objects.filter(away_team=source_team).update(away_team=target_team)
        
        # 3. Remover classificações antigas do time fonte (serão recalculadas)
        LeagueStanding.objects.filter(team=source_team).delete()
        
        # 4. Deletar o time duplicado
        source_team.delete()
