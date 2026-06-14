import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from matches.models import Team, Match
from django.db.models import Q

# 1. Marcar times não mapeados
teams_to_ignore = Team.objects.filter(Q(api_id__isnull=True) | Q(api_id__startswith='sofa_'))
count_teams = 0
for t in teams_to_ignore:
    t.api_id = f"ignored_{t.id}"
    t.save()
    count_teams += 1

# 2. Marcar partidas não mapeadas do passado que ficaram para trás
# (Opcional, mas ajuda a limpar a base do smart_id_mapper)
matches_to_ignore = Match.objects.filter(Q(api_id__isnull=True) | Q(api_id__startswith='sofa_'))
count_matches = 0
for m in matches_to_ignore:
    m.api_id = f"ignored_{m.id}"
    m.save()
    count_matches += 1

print(f"✅ Otimização concluída!")
print(f"Times marcados como histórico: {count_teams}")
print(f"Partidas marcadas como histórico: {count_matches}")
