"""
Django management command to clean up Belgium league data
Removes teams that don't belong to Belgian Pro League
Usage: python manage.py cleanup_belgium --execute
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from matches.models import Match, League, Team, LeagueStanding

class Command(BaseCommand):
    help = 'Clean up Belgium league by removing non-Belgian teams'

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Actually delete the data (dry-run by default)'
        )

    def handle(self, *args, **options):
        execute = options['execute']
        
        if not execute:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be deleted'))
            self.stdout.write('Add --execute to actually delete data\n')
        
        # Find Belgium league
        belgium = League.objects.filter(Q(country__iexact='Belgica') | Q(country__iexact='Belgium')).first()
        
        if not belgium:
            self.stdout.write(self.style.ERROR('Belgium league not found!'))
            return
        
        self.stdout.write(f"League: {belgium.name} (ID: {belgium.id})\n")
        
        # Define correct Belgian teams (from SoccerStats screenshot)
        correct_teams = [
            'Royale Union SG', 'Sint-Truiden', 'Club Brugge', 'Anderlecht',
            'Gent', 'KV Mechelen', 'Mechelen', 'KRC Genk', 'Genk', 
            'Charleroi', 'Westerlo', 'Standard Liege', 'Antwerp',
            'Zulte-Waregem', 'OH Leuven', 'La Louviere', 'Cercle Brugge', 'Dender'
        ]
        
        # Get all teams in Belgium league
        all_teams = Team.objects.filter(league=belgium)
        
        # Identify teams to keep (case-insensitive match)
        teams_to_keep = []
        for team in all_teams:
            for correct_name in correct_teams:
                if correct_name.lower() in team.name.lower() or team.name.lower() in correct_name.lower():
                    teams_to_keep.append(team)
                    break
        
        # Teams to delete
        teams_to_delete = all_teams.exclude(id__in=[t.id for t in teams_to_keep])
        
        self.stdout.write(self.style.SUCCESS(f"Teams to KEEP: {len(teams_to_keep)}"))
        for t in teams_to_keep:
            self.stdout.write(f"  ✓ {t.name}")
        
        self.stdout.write(self.style.WARNING(f"\nTeams to DELETE: {teams_to_delete.count()}"))
        for t in teams_to_delete[:20]:  # Show first 20
            self.stdout.write(f"  ✗ {t.name}")
        if teams_to_delete.count() > 20:
            self.stdout.write(f"  ... and {teams_to_delete.count() - 20} more")
        
        # Find matches involving teams to delete
        matches_to_delete = Match.objects.filter(
            Q(home_team__in=teams_to_delete) | Q(away_team__in=teams_to_delete)
        )
        
        self.stdout.write(f"\nMatches to DELETE: {matches_to_delete.count()}")
        
        # Find standings to delete
        standings_to_delete = LeagueStanding.objects.filter(team__in=teams_to_delete, league=belgium)
        self.stdout.write(f"Standings to DELETE: {standings_to_delete.count()}")
        
        if execute:
            self.stdout.write(self.style.WARNING('\n⚠️  DELETING DATA...'))
            
            # Delete in correct order (foreign key constraints)
            deleted_matches = matches_to_delete.delete()
            self.stdout.write(f"  ✓ Deleted {deleted_matches[0]} matches")
            
            deleted_standings = standings_to_delete.delete()
            self.stdout.write(f"  ✓ Deleted {deleted_standings[0]} standings")
            
            deleted_teams = teams_to_delete.delete()
            self.stdout.write(f"  ✓ Deleted {deleted_teams[0]} teams")
            
            self.stdout.write(self.style.SUCCESS('\n✅ Cleanup complete!'))
            self.stdout.write(f"Remaining teams: {Team.objects.filter(league=belgium).count()}")
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No data was deleted'))
            self.stdout.write('Run with --execute to actually delete')
