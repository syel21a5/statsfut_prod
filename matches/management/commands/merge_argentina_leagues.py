from django.core.management.base import BaseCommand
from django.db import transaction
from matches.models import League, Team, Match

class Command(BaseCommand):
    help = "Move jogos/teams da 'Primera Division' para 'Liga Profesional' (Argentina)"

    def handle(self, *args, **kwargs):
        src = League.objects.filter(name="Primera Division", country="Argentina").first()
        dst = League.objects.filter(name="Liga Profesional", country="Argentina").first()
        if not src:
            self.stdout.write("Liga origem não encontrada")
            return
        if not dst:
            self.stdout.write("Liga destino não encontrada")
            return
        mapping = {}
        for t in Team.objects.filter(league=src):
            tt, _ = Team.objects.get_or_create(name=t.name, league=dst)
            mapping[t.id] = tt.id
        with transaction.atomic():
            qs = Match.objects.filter(league=src)
            total = qs.count()
            for m in qs.iterator(chunk_size=500):
                hid = mapping.get(m.home_team_id)
                aid = mapping.get(m.away_team_id)
                if not hid or not aid:
                    continue
                m.league_id = dst.id
                m.home_team_id = hid
                m.away_team_id = aid
                m.save(update_fields=["league_id", "home_team_id", "away_team_id"])
        self.stdout.write("Concluído")
