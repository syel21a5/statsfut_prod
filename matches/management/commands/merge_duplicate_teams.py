
from django.core.management.base import BaseCommand
from matches.models import Team, Match, League
from django.db.models import Q

class Command(BaseCommand):
    help = 'Merge duplicate teams (e.g. "Rapid Vienna" -> "Rapid Wien") and cleanup leagues'

    def handle(self, *args, **options):
        self.stdout.write("Starting team merge process...")
        
        # Mappings: { 'Wrong Name': 'Correct Name' }
        # Country is optional filter
        merge_map = [
            # AUSTRIA — REMOVIDO!
            # A liga austríaca é gerenciada exclusivamente pelo GitHub Action via SofaScore
            # (atualização a cada 6h). Os nomes dos times são controlados pelo sofascore
            # e qualquer merge aqui vai entrar em conflito e corromper os dados.
            # NÃO adicionar entradas da Áustria aqui.

            # AUSTRALIA — REMOVIDO!
            # Os times australianos são gerenciados exclusivamente pelo SofaScore Action
            # (update_australia.yml). O Action usa api_id para identificar os times,
            # então não há necessidade de renomear aqui.
        ]

        for item in merge_map:
            self.merge_teams(item['wrong'], item['correct'], item.get('country'))

        self.stdout.write(self.style.SUCCESS("Team merge process completed."))

    def merge_teams(self, wrong_name, correct_name, country=None):
        # Find correct team
        query = Q(name=correct_name)
        if country:
            query &= Q(league__country__icontains=country)
        
        correct_team = Team.objects.filter(query).first()
        
        if not correct_team:
            # self.stdout.write(f"Correct team '{correct_name}' not found. Skipping merge of '{wrong_name}'.")
            return

        # Find wrong team(s)
        w_query = Q(name=wrong_name)
        if country:
            w_query &= Q(league__country__icontains=country)
        
        # Exclude the correct team itself if names are similar/same
        wrong_teams = Team.objects.filter(w_query).exclude(id=correct_team.id)

        for wrong_team in wrong_teams:
            if wrong_team.league != correct_team.league:
                self.stdout.write(f"Skipping merge: '{wrong_team}' and '{correct_team}' are in different leagues.")
                continue

            self.stdout.write(f"Merging '{wrong_team.name}' ({wrong_team.id}) into '{correct_team.name}' ({correct_team.id})...")
            
            # Update Matches (Home)
            Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
            # Update Matches (Away)
            Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
            
            # Delete wrong team
            wrong_team.delete()
            self.stdout.write(f"Deleted '{wrong_name}'.")

