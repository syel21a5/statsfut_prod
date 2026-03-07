
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
            # AUSTRIA
            {'wrong': 'Rapid Vienna', 'correct': 'Rapid Wien', 'country': 'Austria'},
            {'wrong': 'Austria Vienna', 'correct': 'Austria Wien', 'country': 'Austria'},
            {'wrong': 'RB Salzburg', 'correct': 'Salzburg', 'country': 'Austria'},
            {'wrong': 'FC Salzburg', 'correct': 'Salzburg', 'country': 'Austria'},
            {'wrong': 'LASK Linz', 'correct': 'LASK', 'country': 'Austria'}, # Scraper uses LASK? Or LASK Linz?
            # Let's check user print. User print has "LASK" (21 games) and "LASK Linz" (20).
            # Soccerstats uses "LASK Linz". Wait, checking print again.
            # User print: "LASK" (21), "LASK Linz" (20).
            # Soccerstats print: "LASK Linz".
            # So "LASK Linz" is likely the scraper one (good). "LASK" is CSV (bad?).
            # Actually CSV usually has "LASK Linz".
            # Let's standardization to "LASK Linz" to match SoccerStats.
            {'wrong': 'LASK', 'correct': 'LASK Linz', 'country': 'Austria'},
            
            {'wrong': 'BW Linz', 'correct': 'Blau-Weiss Linz', 'country': 'Austria'},
            {'wrong': 'Wolfsberger AC', 'correct': 'Wolfsberger AC', 'country': 'Austria'}, # Self map? No.
            # Print shows "Wolfsberger AC" twice? No.
            # Print shows "Wolfsberger AC" and "Wolfsberger".
            {'wrong': 'Wolfsberger', 'correct': 'Wolfsberger AC', 'country': 'Austria'},
            {'wrong': 'A. Klagenfurt', 'correct': 'Austria Klagenfurt', 'country': 'Austria'},
            {'wrong': 'A. Lustenau', 'correct': 'Austria Lustenau', 'country': 'Austria'},
            {'wrong': 'WSG Tirol', 'correct': 'Tirol', 'country': 'Austria'},

            # AUSTRALIA - Removido! Os times australianos são gerenciados
            # exclusivamente pelo SofaScore Action (update_australia.yml).
            # O Action usa api_id para identificar os times, então não há
            # necessidade de renomear aqui. Isso evitava um loop onde o
            # merge renomeava e o Action desfazia a renomeação a cada 6h.
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

