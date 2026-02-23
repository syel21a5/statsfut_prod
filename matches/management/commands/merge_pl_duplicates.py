
from django.core.management.base import BaseCommand
from django.db.models import Q
from matches.models import Team, Match, League, LeagueStanding

class Command(BaseCommand):
    help = 'Merge duplicate Premier League teams (e.g. Leeds -> Leeds Utd)'

    def handle(self, *args, **options):
        # Mapeamento: "Nome Ruim" -> "Nome Bom"
        merges = {
            "Leeds": "Leeds Utd",
            "Newcastle": "Newcastle Utd",
            "West Ham": "West Ham Utd",
            "Wolves": "Wolverhampton",
            "Nottm Forest": "Nottm Forest", # Self-check
            "Nottingham Forest": "Nottm Forest",
            "Leicester": "Leicester", # Self-check
            "Leicester City": "Leicester",
        }

        league_name = "Premier League"
        # Tenta achar a liga
        league = League.objects.filter(name=league_name).first()
        if not league:
            self.stdout.write(self.style.ERROR(f"Liga {league_name} não encontrada."))
            return

        self.stdout.write(f"Processando duplicatas para: {league.name} ({league.country})")

        for bad_name, good_name in merges.items():
            if bad_name == good_name:
                continue

            try:
                bad_team = Team.objects.get(name=bad_name, league=league)
            except Team.DoesNotExist:
                self.stdout.write(f"  - Time duplicado '{bad_name}' não existe (OK).")
                continue
            except Team.MultipleObjectsReturned:
                # Se existirem múltiplos, pega o primeiro e avisa
                bad_team = Team.objects.filter(name=bad_name, league=league).first()
                self.stdout.write(self.style.WARNING(f"  ! Múltiplos times encontrados com nome '{bad_name}'. Usando o primeiro ID={bad_team.id}."))

            try:
                good_team = Team.objects.get(name=good_name, league=league)
            except Team.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"  x Time destino '{good_name}' não existe! Não é possível migrar '{bad_name}'."))
                # Se o good team não existe, talvez devêssemos renomear o bad team para good team?
                # Mas o user disse que o good team já tem pontos, então ele deve existir.
                # Vamos tentar buscar por contains se falhar
                candidates = Team.objects.filter(name__icontains=good_name, league=league)
                if candidates.exists():
                    good_team = candidates.first()
                    self.stdout.write(self.style.SUCCESS(f"    -> Encontrado candidato '{good_team.name}' (ID={good_team.id}). Usando este."))
                else:
                    continue

            self.stdout.write(f"  > Mesclando '{bad_team.name}' (ID={bad_team.id}) -> '{good_team.name}' (ID={good_team.id})...")

            # 1. Atualizar Jogos (Home)
            matches_home = Match.objects.filter(home_team=bad_team)
            count_home = matches_home.count()
            matches_home.update(home_team=good_team)
            
            # 2. Atualizar Jogos (Away)
            matches_away = Match.objects.filter(away_team=bad_team)
            count_away = matches_away.count()
            matches_away.update(away_team=good_team)

            self.stdout.write(f"    - Jogos migrados: {count_home} (casa) + {count_away} (fora)")

            # 3. Remover Standings do time ruim
            LeagueStanding.objects.filter(team=bad_team).delete()
            self.stdout.write("    - Classificações removidas.")

            # 4. Deletar time ruim
            bad_team.delete()
            self.stdout.write(self.style.SUCCESS(f"    - Time '{bad_name}' DELETADO com sucesso."))

        self.stdout.write(self.style.SUCCESS("\nConcluído! Agora rode o recalculate_standings."))
