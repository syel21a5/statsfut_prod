import os
import sys
import django  # type: ignore

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match  # type: ignore
from django.db import transaction  # type: ignore

def consolidate():
    # Mapping: (Canonical ID, Old ID that should be merged)
    # We prefer the one with Sofa API ID already or the one with more matches
    merges = [
        (1456, 722), # Young Boys
        (1457, 725), # Lugano
        (1459, 721), # Luzern
        (1458, 729), # Sion
        (1462, 724), # St. Gallen
        (1465, 726), # Zurich
        (1467, 730), # Servette
        (1461, 727), # Grasshoppers
        (1463, 723), # Lausanne
        (1460, 735), # Thun
    ]

    with transaction.atomic():
        for canonical_id, old_id in merges:
            try:
                c_team = Team.objects.get(id=canonical_id)
                o_team = Team.objects.get(id=old_id)
                
                print(f"Merge: {o_team.name} ({old_id}) -> {c_team.name} ({canonical_id})")
                
                # Update home matches
                h_count = Match.objects.filter(home_team=o_team).update(home_team=c_team)
                # Update away matches
                a_count = Match.objects.filter(away_team=o_team).update(away_team=c_team)
                
                print(f"  Moved {h_count} home and {a_count} away matches.")
                
                # Delete old team
                o_team.delete()
                print(f"  Deleted old team {old_id}.")
                
            except Team.DoesNotExist:
                print(f"  Skipping {canonical_id} or {old_id} (one doesn't exist)")

    print("\nConsolidação concluída.")

if __name__ == "__main__":
    consolidate()
