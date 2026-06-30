from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, LeagueStanding, TeamGoalTiming
from django.db import transaction

class Command(BaseCommand):
    help = 'Merges Serie A (Brazil) into Brasileirão and deletes the duplicate league.'

    def handle(self, *args, **options):
        try:
            brasileirao = League.objects.get(name__icontains='Brasileirão', country__icontains='Brazil')
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR("Brasileirão league not found."))
            try:
                brasileirao = League.objects.get(name__icontains='Brasileirão', country__icontains='Brasil')
            except League.DoesNotExist:
                return

        try:
            serie_a = League.objects.get(name='Serie A', country__icontains='Brazil')
        except League.DoesNotExist:
            try:
                serie_a = League.objects.get(name='Serie A', country__icontains='Brasil')
            except League.DoesNotExist:
                self.stdout.write(self.style.SUCCESS("No Serie A duplicate found for Brazil. All good!"))
                return
        
        self.stdout.write(self.style.WARNING(f"Merging {serie_a.name} into {brasileirao.name}..."))
        
        with transaction.atomic():
            # 1. Move Teams
            for team in serie_a.teams.all():
                existing_team = Team.objects.filter(name=team.name, league=brasileirao).first()
                if existing_team:
                    self.stdout.write(f"Team {team.name} already in Brasileirão. Merging records...")
                    
                    # Safe Match transfer
                    for match in Match.objects.filter(home_team=team):
                        # Se já existe um jogo no mesmo dia com os mesmos times, deleta a duplicata
                        if Match.objects.filter(home_team=existing_team, away_team=match.away_team, date=match.date).exists():
                            match.delete()
                        else:
                            match.home_team = existing_team
                            match.league = brasileirao
                            match.save()
                            
                    for match in Match.objects.filter(away_team=team):
                        if Match.objects.filter(home_team=match.home_team, away_team=existing_team, date=match.date).exists():
                            match.delete()
                        else:
                            match.away_team = existing_team
                            match.league = brasileirao
                            match.save()
                    
                    for standing in LeagueStanding.objects.filter(team=team):
                        if LeagueStanding.objects.filter(team=existing_team, season=standing.season).exists():
                            standing.delete()
                        else:
                            standing.team = existing_team
                            standing.league = brasileirao
                            standing.save()
                    
                    TeamGoalTiming.objects.filter(team=team).update(team=existing_team, league=brasileirao)
                    team.delete()
                else:
                    self.stdout.write(f"Moving team {team.name} to Brasileirão.")
                    team.league = brasileirao
                    team.save()

            # 2. Move remaining related objects safely
            for match in Match.objects.filter(league=serie_a):
                if Match.objects.filter(home_team=match.home_team, away_team=match.away_team, date=match.date).exists():
                    match.delete()
                else:
                    match.league = brasileirao
                    match.save()
                    
            LeagueStanding.objects.filter(league=serie_a).update(league=brasileirao)
            TeamGoalTiming.objects.filter(league=serie_a).update(league=brasileirao)
            
            # Fix all group names to 'Serie A' so they don't split into multiple tabs
            LeagueStanding.objects.filter(league=brasileirao).update(group_name='Serie A')

            # 3. Delete the duplicate league
            serie_a.delete()
            
            # Clear cache
            from django.core.cache import cache
            cache.clear()
            
        self.stdout.write(self.style.SUCCESS("Successfully merged Serie A into Brasileirão!"))
