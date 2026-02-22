
from django.core.management.base import BaseCommand
from django.db import transaction
from matches.models import League, Team, Match, LeagueStanding, Goal, Player, TeamGoalTiming

class Command(BaseCommand):
    help = "Mescla ligas duplicadas (ex: 'Brasileirão' -> 'Brasileirao')"

    def handle(self, *args, **options):
        # Defina aqui os pares (Nome Ruim, Nome Bom, País)
        # O script assume que o país é o mesmo ou irrelevante se o nome for único
        MERGES = [
            ("Brasileirão", "Brasileirao", "Brasil"),
            ("Ligue 1", "Ligue 1", "França"), # Exemplo hipotético se houver duplicata por acento no país
        ]

        for bad_name, good_name, country in MERGES:
            self._merge_league(bad_name, good_name, country)

    def _merge_league(self, bad_name, good_name, country):
        try:
            # Tenta encontrar a liga "ruim"
            # Pode haver variações no país, então filtramos pelo nome primeiro
            bad_leagues = League.objects.filter(name=bad_name)
            if country:
                 bad_leagues = bad_leagues.filter(country=country)
            
            if not bad_leagues.exists():
                self.stdout.write(f"Liga '{bad_name}' não encontrada. Pular.")
                return

            # Tenta encontrar a liga "boa"
            good_league = League.objects.filter(name=good_name)
            if country:
                good_league = good_league.filter(country=country)
            
            good_league = good_league.first()

            if not good_league:
                # Se a boa não existe, renomeia a ruim para a boa
                bad_league = bad_leagues.first()
                bad_league.name = good_name
                bad_league.save()
                self.stdout.write(self.style.SUCCESS(f"Renomeado '{bad_name}' para '{good_name}'"))
                return

            # Se ambas existem, mescla
            for bad_league in bad_leagues:
                if bad_league.id == good_league.id:
                    continue
                
                self.stdout.write(self.style.WARNING(f"Mesclando '{bad_league.name}' (ID {bad_league.id}) -> '{good_league.name}' (ID {good_league.id})"))
                
                with transaction.atomic():
                    # Mover Times
                    teams = Team.objects.filter(league=bad_league)
                    count_teams = teams.count()
                    teams.update(league=good_league)
                    
                    # Mover Partidas
                    matches = Match.objects.filter(league=bad_league)
                    count_matches = matches.count()
                    matches.update(league=good_league)
                    
                    # Mover Standings
                    standings = LeagueStanding.objects.filter(league=bad_league)
                    standings.update(league=good_league)

                    # Deletar liga antiga
                    bad_league.delete()
                
                self.stdout.write(self.style.SUCCESS(f"  -> Movidos {count_teams} times e {count_matches} jogos."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao mesclar ligas: {e}"))
