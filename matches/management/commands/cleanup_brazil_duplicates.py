import logging
from django.core.management.base import BaseCommand
from django.db.models import Q
from matches.models import Team, League, Match, LeagueStanding

class Command(BaseCommand):
    help = "Limpa times duplicados do Brasileirão (mesclando jogos e removendo duplicatas)"

    def handle(self, *args, **options):
        self.stdout.write("Iniciando limpeza de duplicatas do Brasileirão...")

        # 1. Identificar a Liga
        leagues = League.objects.filter(name__icontains="Brasileir")
        if not leagues.exists():
            self.stdout.write(self.style.ERROR("Liga Brasileirão não encontrada!"))
            return
        
        # Pode haver mais de uma liga com nome similar, vamos iterar por todas para garantir
        for league in leagues:
            self.stdout.write(f"Processando Liga: {league.name} (ID: {league.id})")
            self.clean_league(league)

        self.stdout.write(self.style.SUCCESS("Limpeza concluída!"))

    def clean_league(self, league):
        # Lista de mapeamento (Nome Errado -> Nome Correto)
        # Baseado nos prints e logs
        duplicates_map = {
            "Chapecoense AF": "Chapecoense",
            "Associação Chapecoense de Futebol": "Chapecoense",
            "CA Paranaense": "Athletico-PR",
            "Club Athletico Paranaense": "Athletico-PR",
            "CA Mineiro": "Atletico-MG",
            "Clube Atlético Mineiro": "Atletico-MG",
            "RB Bragantino": "Bragantino",
            "Red Bull Bragantino": "Bragantino",
            "Coritiba FBC": "Coritiba",
            "Coritiba FC": "Coritiba",
            "Mirassol FC": "Mirassol",
            "Clube do Remo": "Remo",
            "Sport Club do Recife": "Sport Recife",
            "Ceará SC": "Ceara",
            "Goiás EC": "Goias",
            "América FC": "America-MG",
            "Avaí FC": "Avai",
            "Paysandu SC": "Paysandu",
            "Vila Nova FC": "Vila Nova",
            "Grêmio Novorizontino": "Novorizontino",
        }

        for bad_name, correct_name in duplicates_map.items():
            self.merge_teams(league, bad_name, correct_name)

    def merge_teams(self, league, bad_name, correct_name):
        # Busca o time errado (case insensitive)
        bad_team = Team.objects.filter(name__iexact=bad_name, league=league).first()
        if not bad_team:
            # self.stdout.write(f"  - Time duplicado '{bad_name}' não encontrado nesta liga. (OK)")
            return

        # Busca o time correto
        correct_team = Team.objects.filter(name__iexact=correct_name, league=league).first()
        if not correct_team:
            self.stdout.write(self.style.WARNING(f"  - Time CORRETO '{correct_name}' não encontrado! Renomeando '{bad_name}' para '{correct_name}'..."))
            bad_team.name = correct_name
            bad_team.save()
            return

        self.stdout.write(f"  -> Mesclando '{bad_team.name}' (ID: {bad_team.id}) em '{correct_team.name}' (ID: {correct_team.id})...")

        # 1. Atualizar Jogos (Home)
        Match.objects.filter(home_team=bad_team).update(home_team=correct_team)
        
        # 2. Atualizar Jogos (Away)
        Match.objects.filter(away_team=bad_team).update(away_team=correct_team)

        # 3. Atualizar Standings (se houver)
        # Se já existir standing para o time correto, deleta o do time errado.
        # Se não, move para o time correto.
        bad_standings = LeagueStanding.objects.filter(team=bad_team)
        for bs in bad_standings:
            if LeagueStanding.objects.filter(team=correct_team, league=bs.league, season=bs.season).exists():
                bs.delete()
            else:
                bs.team = correct_team
                bs.save()

        # 4. Remover Time Errado
        try:
            # Se tiver API ID e o correto não tiver, transfere (se não der conflito)
            if bad_team.api_id and not correct_team.api_id:
                correct_team.api_id = bad_team.api_id
                correct_team.save()
            
            bad_team.delete()
            self.stdout.write(self.style.SUCCESS(f"     '{bad_name}' removido com sucesso."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"     Erro ao remover '{bad_name}': {e}"))
