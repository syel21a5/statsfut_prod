from django.core.management.base import BaseCommand
from matches.models import Match, League, Team
from django.db.models import Q

class Command(BaseCommand):
    help = 'Remove jogos de copa (não-Premier League) que foram importados por engano'

    def handle(self, *args, **options):
        try:
            league = League.objects.get(name="Premier League")
            
            # Times que NÃO estão na Premier League 2025/2026
            non_pl_teams = [
                "Sunderland",
                "Sunderland AFC",
            ]
            
            deleted_count = 0
            
            for team_name in non_pl_teams:
                # Busca jogos envolvendo esses times na Premier League
                matches = Match.objects.filter(
                    league=league
                ).filter(
                    Q(home_team__name=team_name) | Q(away_team__name=team_name)
                )
                
                if matches.exists():
                    self.stdout.write(f"\n🗑️  Removendo {matches.count()} jogo(s) envolvendo {team_name}:")
                    for match in matches:
                        self.stdout.write(f"  - {match.date.date() if match.date else 'No Date'}: {match.home_team} {match.home_score}x{match.away_score} {match.away_team}")
                        match.delete()
                        deleted_count += 1
            
            if deleted_count > 0:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Total removido: {deleted_count} jogo(s)"))
                self.stdout.write(self.style.WARNING("\n⚠️  IMPORTANTE: Rode 'recalculate_standings' para atualizar a tabela!"))
            else:
                self.stdout.write(self.style.SUCCESS("✅ Nenhum jogo de copa encontrado"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))
