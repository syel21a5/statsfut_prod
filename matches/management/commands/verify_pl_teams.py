from django.core.management.base import BaseCommand
from matches.models import League, Team, Match

class Command(BaseCommand):
    help = 'Verifica quais times da Premier League 2025/2026 estão no banco'

    def handle(self, *args, **options):
        try:
            league = League.objects.get(name="Premier League")
            
            # Lista oficial dos 20 times da Premier League 2025/2026
            official_teams = [
                "Arsenal",
                "Manchester City",
                "Aston Villa",
                "Chelsea",
                "Manchester Utd",
                "Liverpool",
                "Bournemouth",
                "Brentford",
                "Newcastle Utd",
                "Everton",
                "Crystal Palace",
                "Fulham",
                "Brighton",
                "Leeds Utd",
                "Tottenham",
                "Nottm Forest",
                "West Ham Utd",
                "Burnley",
                "Wolverhampton",
                "Ipswich",
            ]
            
            self.stdout.write("\n📋 Verificando times da Premier League 2025/2026:\n")
            
            found_teams = []
            missing_teams = []
            
            for team_name in official_teams:
                team = Team.objects.filter(name=team_name, league=league).first()
                if team:
                    # Conta jogos desse time
                    home_matches = Match.objects.filter(home_team=team, league=league).count()
                    away_matches = Match.objects.filter(away_team=team, league=league).count()
                    total_matches = home_matches + away_matches
                    
                    found_teams.append(team_name)
                    self.stdout.write(f"  ✅ {team_name}: {total_matches} jogos")
                else:
                    missing_teams.append(team_name)
                    self.stdout.write(self.style.WARNING(f"  ❌ {team_name}: NÃO ENCONTRADO"))
            
            # Verifica se há times extras (que não deveriam estar)
            all_teams = Team.objects.filter(league=league)
            extra_teams = []
            
            for team in all_teams:
                if team.name not in official_teams:
                    home_matches = Match.objects.filter(home_team=team, league=league).count()
                    away_matches = Match.objects.filter(away_team=team, league=league).count()
                    total_matches = home_matches + away_matches
                    
                    if total_matches > 0:
                        extra_teams.append(team.name)
                        self.stdout.write(self.style.ERROR(f"  ⚠️  {team.name}: {total_matches} jogos (NÃO DEVERIA ESTAR NA PL!)"))
            
            self.stdout.write(f"\n📊 Resumo:")
            self.stdout.write(f"  ✅ Times encontrados: {len(found_teams)}/20")
            self.stdout.write(f"  ❌ Times faltando: {len(missing_teams)}")
            self.stdout.write(f"  ⚠️  Times extras: {len(extra_teams)}")
            
            if missing_teams:
                self.stdout.write(f"\n🔍 Times faltando: {', '.join(missing_teams)}")
            
            if extra_teams:
                self.stdout.write(f"\n⚠️  Times extras: {', '.join(extra_teams)}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {e}"))

verify_pl_teams()
