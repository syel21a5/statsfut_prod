"""
Django management command to diagnose Belgium league data
Usage: python manage.py diagnose_belgium
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from matches.models import Match, League, Team, Season, LeagueStanding
from django.utils import timezone

class Command(BaseCommand):
    help = 'Diagnose Belgium league data issues'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== DIAGNOSING BELGIUM DATA ===\n'))
        
        # 1. Find Belgium league
        belgium = League.objects.filter(Q(country__iexact='Belgica') | Q(country__iexact='Belgium')).first()
        
        if not belgium:
            self.stdout.write(self.style.ERROR('Belgium league not found!'))
            return
        
        self.stdout.write(f"League: {belgium.name} (ID: {belgium.id}, Country: {belgium.country})\n")
        
        # 2. Check teams
        teams = Team.objects.filter(league=belgium).order_by('name')
        self.stdout.write(f"Total Teams: {teams.count()}\n")
        
        if teams.count() > 0:
            self.stdout.write("Teams:")
            for t in teams:
                self.stdout.write(f"  - {t.name} (ID: {t.id})")
        
        # 3. Check for teams with non-Belgian names
        self.stdout.write("\n=== CHECKING FOR INCORRECT TEAMS ===")
        brazilian_keywords = ['Chapecoense', 'Botafogo', 'Mirassol', 'Gremio', 'Santos', 'Sao Paulo', 'Coritiba', 'Fluminense', 'Cruzeiro']
        french_keywords = ['Paris', 'Marseille', 'Lyon', 'Lille', 'Monaco']
        
        for keyword in brazilian_keywords + french_keywords:
            wrong_teams = teams.filter(name__icontains=keyword)
            if wrong_teams.exists():
                self.stdout.write(self.style.WARNING(f"  ⚠️  Found '{keyword}' in Belgium league:"))
                for t in wrong_teams:
                    self.stdout.write(f"      - {t.name} (ID: {t.id})")
        
        # 4. Check matches
        season_2026 = Season.objects.filter(year=2026).first()
        if not season_2026:
            self.stdout.write(self.style.WARNING("\nSeason 2026 not found!"))
            return
        
        matches = Match.objects.filter(league=belgium, season=season_2026)
        self.stdout.write(f"\n=== MATCHES IN 2026 ===")
        self.stdout.write(f"Total: {matches.count()}")
        
        # Group by status
        status_counts = matches.values('status').annotate(count=Count('id')).order_by('-count')
        self.stdout.write("\nBy Status:")
        for s in status_counts:
            self.stdout.write(f"  {s['status']}: {s['count']}")
        
        # 5. Check standings
        standings = LeagueStanding.objects.filter(league=belgium, season=season_2026).order_by('position')
        self.stdout.write(f"\n=== STANDINGS ===")
        self.stdout.write(f"Total entries: {standings.count()}")
        
        if standings.exists():
            self.stdout.write("\nCurrent Standings:")
            self.stdout.write(f"{'#':<3} {'Team':<25} {'GP':<4} {'Pts':<4}")
            self.stdout.write("-" * 40)
            for s in standings:
                self.stdout.write(f"{s.position:<3} {s.team.name:<25} {s.played:<4} {s.points:<4}")
        
        # 6. Check for matches with teams from other leagues
        self.stdout.write("\n=== CHECKING FOR CROSS-LEAGUE MATCHES ===")
        cross_league = matches.exclude(home_team__league=belgium) | matches.exclude(away_team__league=belgium)
        if cross_league.exists():
            self.stdout.write(self.style.WARNING(f"Found {cross_league.count()} matches with teams from other leagues:"))
            for m in cross_league[:10]:
                self.stdout.write(f"  {m.home_team.name} ({m.home_team.league.name}) vs {m.away_team.name} ({m.away_team.league.name})")
        else:
            self.stdout.write(self.style.SUCCESS("✓ No cross-league matches found"))
        
        # 7. Check recent imports
        self.stdout.write("\n=== LAST 10 MATCHES CREATED ===")
        recent = Match.objects.filter(league=belgium).order_by('-id')[:10]
        for m in recent:
            self.stdout.write(f"ID: {m.id} | {m.home_team.name} vs {m.away_team.name} | {m.date} | {m.status}")
        
        self.stdout.write(self.style.SUCCESS('\n✅ Diagnosis complete!'))
