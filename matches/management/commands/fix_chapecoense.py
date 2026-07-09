from django.core.management.base import BaseCommand
from matches.models import Match, Team, Goal, LeagueStanding

class Command(BaseCommand):
    help = "Funde a Chapecoense-sc (clone) na Chapecoense original no banco de dados."

    def handle(self, *args, **options):
        try:
            t_old = Team.objects.get(id=5285)
            t_new = Team.objects.get(id=5396)
        except Team.DoesNotExist:
            self.stdout.write(self.style.SUCCESS("A Chapecoense clone ja foi resolvida ou nao existe neste banco! Tudo certo!"))
            return

        self.stdout.write("Iniciando fusao da Chapecoense...")

        new_id = t_new.api_id
        t_new.api_id = None
        t_new.save(update_fields=['api_id'])

        t_old.api_id = new_id
        t_old.save(update_fields=['api_id'])

        for m in Match.objects.filter(home_team=t_new):
            try:
                m.home_team = t_old
                m.save(update_fields=['home_team'])
            except Exception:
                m.delete()

        for m in Match.objects.filter(away_team=t_new):
            try:
                m.away_team = t_old
                m.save(update_fields=['away_team'])
            except Exception:
                m.delete()

        Goal.objects.filter(team=t_new).update(team=t_old)

        for std in LeagueStanding.objects.filter(team=t_new):
            try:
                std.team = t_old
                std.save(update_fields=['team'])
            except Exception:
                std.delete()

        t_new.delete()
        self.stdout.write(self.style.SUCCESS("Chapecoense fundida com sucesso no SERVIDOR!"))
