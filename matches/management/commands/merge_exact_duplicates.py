from django.core.management.base import BaseCommand
from matches.models import Team, Match
from django.db.models import Count, Q
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Merge exactly duplicated team names in the database'

    def handle(self, *args, **options):
        duplicates = Team.objects.values('name', 'league__country').annotate(c=Count('id')).filter(c__gt=1)

        for d in duplicates:
            name = d['name']
            country = d['league__country']
            
            teams = list(Team.objects.filter(name=name, league__country=country).order_by('-api_id'))
            if len(teams) > 1:
                correct_team = teams[0]
                wrong_teams = teams[1:]
                
                self.stdout.write(f'Merging {len(wrong_teams)} duplicates for {name} ({country})')
                
                for wrong_team in wrong_teams:
                    if wrong_team.api_id and not correct_team.api_id:
                        correct_team.api_id = wrong_team.api_id
                        correct_team.save()
                        wrong_team.api_id = None
                        wrong_team.save()
                        
                    for m in Match.objects.filter(home_team=wrong_team):
                        m.home_team = correct_team
                        try:
                            m.save()
                        except IntegrityError:
                            conflicting = Match.objects.filter(home_team=correct_team, away_team=m.away_team, date__date=m.date.date()).exclude(id=m.id).first()
                            if conflicting and not conflicting.home_score and m.home_score:
                                conflicting.home_score = m.home_score
                                conflicting.away_score = m.away_score
                                conflicting.status = m.status
                                conflicting.save()
                            m.delete()
                            
                    for m in Match.objects.filter(away_team=wrong_team):
                        m.away_team = correct_team
                        try:
                            m.save()
                        except IntegrityError:
                            conflicting = Match.objects.filter(home_team=m.home_team, away_team=correct_team, date__date=m.date.date()).exclude(id=m.id).first()
                            if conflicting and not conflicting.home_score and m.home_score:
                                conflicting.home_score = m.home_score
                                conflicting.away_score = m.away_score
                                conflicting.status = m.status
                                conflicting.save()
                            m.delete()
                    
                    if not Match.objects.filter(Q(home_team=wrong_team) | Q(away_team=wrong_team)).exists():
                        wrong_team.delete()
        self.stdout.write(self.style.SUCCESS('All exact duplicates merged!'))
