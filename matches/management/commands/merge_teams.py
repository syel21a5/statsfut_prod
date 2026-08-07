from django.core.management.base import BaseCommand
from matches.models import Team, Match, LeagueStanding
from django.db import transaction

class Command(BaseCommand):
    help = 'Faz a fusão (merge) de um time duplicado criado pela API para o time original (SofaScore)'

    def add_arguments(self, parser):
        parser.add_argument('--bad_id', type=int, required=True, help='ID do time "Fantasma" criado pela API')
        parser.add_argument('--good_id', type=int, required=True, help='ID do time Original/Correto')

    def handle(self, *args, **options):
        bad_id = options['bad_id']
        good_id = options['good_id']

        try:
            bad_team = Team.objects.get(id=bad_id)
        except Team.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Time ruim (ID {bad_id}) não encontrado no banco."))
            return

        try:
            good_team = Team.objects.get(id=good_id)
        except Team.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Time bom (ID {good_id}) não encontrado no banco."))
            return

        self.stdout.write(self.style.SUCCESS(f"Iniciando fusão: '{bad_team.name}' (Fantasma) -> '{good_team.name}' (Original)"))

        with transaction.atomic():
            # 1. Transferir partidas onde o time ruim foi Mandante
            bad_home_matches = Match.objects.filter(home_team=bad_team)
            for bm in bad_home_matches:
                # Verifica se o time bom já tem partida nesse dia contra esse adversario
                existing_good_match = Match.objects.filter(
                    home_team=good_team,
                    away_team=bm.away_team,
                    date__date=bm.date.date()
                ).first()

                if existing_good_match:
                    self.stdout.write(f"  [Conflito Casa] O {good_team.name} já tem jogo contra {bm.away_team.name} em {bm.date.date()}. Mesclando dados API...")
                    # Transferir dados ricos (API ID, corners, stats)
                    if not existing_good_match.api_id and bm.api_id:
                        existing_good_match.api_id = bm.api_id
                    existing_good_match.home_corners = bm.home_corners
                    existing_good_match.away_corners = bm.away_corners
                    existing_good_match.home_score = bm.home_score
                    existing_good_match.away_score = bm.away_score
                    if bm.status in ['FT', 'Finished', 'AET', 'PEN']:
                        existing_good_match.status = bm.status
                    existing_good_match.save()
                    # Transfere os gols (Goal objects)
                    bm.goals.all().update(match=existing_good_match)
                    bm.delete()
                else:
                    self.stdout.write(f"  [Transferindo Casa] Jogo contra {bm.away_team.name} movido direto.")
                    bm.home_team = good_team
                    bm.save()

            # 2. Transferir partidas onde o time ruim foi Visitante
            bad_away_matches = Match.objects.filter(away_team=bad_team)
            for bm in bad_away_matches:
                existing_good_match = Match.objects.filter(
                    home_team=bm.home_team,
                    away_team=good_team,
                    date__date=bm.date.date()
                ).first()

                if existing_good_match:
                    self.stdout.write(f"  [Conflito Fora] O {good_team.name} já tem jogo contra {bm.home_team.name} em {bm.date.date()}. Mesclando dados API...")
                    if not existing_good_match.api_id and bm.api_id:
                        existing_good_match.api_id = bm.api_id
                    existing_good_match.home_corners = bm.home_corners
                    existing_good_match.away_corners = bm.away_corners
                    existing_good_match.home_score = bm.home_score
                    existing_good_match.away_score = bm.away_score
                    if bm.status in ['FT', 'Finished', 'AET', 'PEN']:
                        existing_good_match.status = bm.status
                    existing_good_match.save()
                    bm.goals.all().update(match=existing_good_match)
                    bm.delete()
                else:
                    self.stdout.write(f"  [Transferindo Fora] Jogo contra {bm.home_team.name} movido direto.")
                    bm.away_team = good_team
                    bm.save()
            
            # 3. Mover Standings
            LeagueStanding.objects.filter(team=bad_team).delete() # Se for standings da API, removemos pq o sofascore tem a dele
            
            # 4. Transferir API ID e deletar
            api_id_to_transfer = bad_team.api_id
            
            bad_team.api_id = None
            bad_team.save()

            if api_id_to_transfer:
                good_team.api_id = api_id_to_transfer
                good_team.save()
                self.stdout.write(self.style.SUCCESS(f"  [+] API_ID '{api_id_to_transfer}' transferido com sucesso para '{good_team.name}'"))
            
            # Deletar o time fantasma
            bad_team.delete()
            self.stdout.write(self.style.SUCCESS(f"\nFusão completa! O time fantasma foi apagado e o banco está limpo."))
