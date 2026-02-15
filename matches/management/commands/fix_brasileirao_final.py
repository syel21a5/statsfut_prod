from django.core.management.base import BaseCommand
from matches.models import Team, Match, League, Season, LeagueStanding
from django.db.models import Q
import re

class Command(BaseCommand):
    help = 'Fix duplicate teams in Brasileirao (v2)'

    def handle(self, *args, **options):
        self.stdout.write("Starting fix for Brasileirao duplicates (All Seasons)...")
        
        # 1. Identify the League
        try:
            league = League.objects.filter(name__icontains='Brasileir').first()
        except:
            self.stdout.write("Brasileirao league not found.")
            return

        if not league:
            self.stdout.write("Brasileirao league not found.")
            return

        self.stdout.write(f"League: {league.name} (ID: {league.id})")

        # Debug: Print all teams summary
        total_teams = Team.objects.count()
        self.stdout.write(f"\nTotal Teams in DB: {total_teams}")

        # Map bad -> good
        # Format: 'Bad Name': 'Good Name'
        # We want to keep the simple names (e.g. 'Botafogo', 'Flamengo')
        # and merge the others (e.g. 'Botafogo RJ', 'Flamengo RJ') into them.
        
        # Key = Bad Name (to be removed)
        # Value = Good Name (to keep)
        dupes_map = {
            'Botafogo RJ': 'Botafogo',
            'Flamengo RJ': 'Flamengo',
            'Chapecoense-SC': 'Chapecoense AF',
            'CA Mineiro': 'Atletico-MG',
            'CA Paranaense': 'Athletico-PR',
            'EC Bahia': 'Bahia',
            'RB Bragantino': 'Bragantino',
            'Coritiba FBC': 'Coritiba',
            'Clube do Remo': 'Remo',
            'Mirassol FC': 'Mirassol',
            'Santos FC': 'Santos',
            'Criciuma EC': 'Criciuma',
            'Gremio FBPA': 'Gremio',
            'EC Vitoria': 'Vitoria',
            'Vitoria BA': 'Vitoria',
            'EC Juventude': 'Juventude',
            'Fortaleza EC': 'Fortaleza',
            'Cuiaba EC': 'Cuiaba',
            'Goias EC': 'Goias',
            'America-MG': 'America MG',
            'Atletico-GO': 'Atletico GO',
            'Sao Paulo FC': 'Sao Paulo',
            'SC Internacional': 'Internacional',
            'Fluminense FC': 'Fluminense',
            'Vasco da Gama': 'Vasco',
            'CR Vasco da Gama': 'Vasco',
            'Cruzeiro EC': 'Cruzeiro',
            'Sport Club Corinthians Paulista': 'Corinthians',
            'SC Corinthians Paulista': 'Corinthians',
            'SE Palmeiras': 'Palmeiras',
        }

        # Helper to find canonical team
        def get_canonical_team(name_map, bad_name):
            good_name = name_map.get(bad_name)
            if not good_name:
                return None
            # Find the good team object
            # First try in the same league
            gt = Team.objects.filter(name=good_name, league=league).first()
            if not gt:
                # Try global search
                gt = Team.objects.filter(name=good_name).first()
            return gt

        for bad_name, good_name in dupes_map.items():
            self.stdout.write(f"\nProcessing {bad_name} -> {good_name}...")
            
            # Find bad team(s)
            bad_teams = Team.objects.filter(name=bad_name)
            if not bad_teams.exists():
                self.stdout.write(f"  {bad_name} not found. Skipping.")
                continue

            # Find good team
            good_team = Team.objects.filter(name=good_name, league=league).first()
            if not good_team:
                good_team = Team.objects.filter(name=good_name).first()
            
            if not good_team:
                self.stdout.write(f"  Target team {good_name} not found! Creating it...")
                good_team = Team.objects.create(name=good_name, league=league)

            self.stdout.write(f"  Target: {good_team.name} (ID: {good_team.id})")

            for bad_team in bad_teams:
                if bad_team.id == good_team.id:
                    continue
                
                self.stdout.write(f"  Merging {bad_team.name} (ID: {bad_team.id}) into target...")

                # 1. Update Matches
                # Update home matches
                Match.objects.filter(home_team=bad_team).update(home_team=good_team)
                # Update away matches
                Match.objects.filter(away_team=bad_team).update(away_team=good_team)

                # 2. Update Standings
                # If good team already has standing for a season, delete bad team's standing
                # If not, move it.
                standings = LeagueStanding.objects.filter(team=bad_team)
                for s in standings:
                    if LeagueStanding.objects.filter(team=good_team, season=s.season, league=s.league).exists():
                        s.delete()
                    else:
                        s.team = good_team
                        s.save()

                # 3. Delete Bad Team
                bad_team.delete()
                self.stdout.write("  Merged and deleted.")

        # 4. Garbage Collection
        self.stdout.write("\nChecking for garbage teams...")
        all_teams = Team.objects.all()
        garbage_count = 0
        for team in all_teams:
            name = team.name
            if re.match(r'^\d', name) or \
               name.startswith('(') or \
               '%' in name or \
               'Copyright' in name or \
               'Privacy' in name or \
               'Match dates' in name or \
               'Average' in name or \
               'Offence' in name or \
               'Defence' in name or \
               'Home' in name or \
               'Away' in name or \
               'Segment' in name or \
               'Contact' in name or \
               'Pts' in name or \
               'MATCHES' in name or \
               'Over ' in name or \
               'Form (' in name or \
               len(name) < 3:
                
                self.stdout.write(f"  Found garbage team: {name} (ID: {team.id})")
                matches = Match.objects.filter(Q(home_team=team) | Q(away_team=team))
                if matches.count() > 0:
                    self.stdout.write(f"    WARNING: Team has {matches.count()} matches. Deleting matches first.")
                    matches.delete()
                team.delete()
                garbage_count += 1
        
        self.stdout.write(f"Deleted {garbage_count} garbage teams.")
        self.stdout.write("Fix completed.")
