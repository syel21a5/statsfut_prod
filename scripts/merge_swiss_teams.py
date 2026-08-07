import os
import sys
import django
from django.db import transaction

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, LeagueStanding, Goal, TeamGoalTiming

def merge_teams(source_name, target_name, league_country='Suica'):
    try:
        source_team = Team.objects.filter(name=source_name, league__country=league_country).first()
        target_team = Team.objects.filter(name=target_name, league__country=league_country).first()

        if not source_team:
            print(f"Source team '{source_name}' not found. Skipping.")
            return

        if not target_team:
            print(f"Target team '{target_name}' not found. Renaming source...")
            source_team.name = target_name
            source_team.save()
            print(f"Renamed '{source_name}' to '{target_name}'")
            return

        print(f"Merging '{source_name}' (ID: {source_team.id}) into '{target_name}' (ID: {target_team.id})...")

        with transaction.atomic():
            # 1. Update Matches
            Match.objects.filter(home_team=source_team).update(home_team=target_team)
            Match.objects.filter(away_team=source_team).update(away_team=target_team)
            
            # 2. Update Standings
            # Handle potential duplicates in standings (same season)
            source_standings = LeagueStanding.objects.filter(team=source_team)
            for ss in source_standings:
                if LeagueStanding.objects.filter(team=target_team, season=ss.season, league=ss.league).exists():
                    ss.delete() # Delete duplicate source standing
                else:
                    ss.team = target_team
                    ss.save()

            # 3. Update Goals
            Goal.objects.filter(team=source_team).update(team=target_team)
            
            # 4. Update Goal Timings
            source_timings = TeamGoalTiming.objects.filter(team=source_team)
            for st in source_timings:
                if TeamGoalTiming.objects.filter(team=target_team, season=st.season, league=st.league).exists():
                    st.delete()
                else:
                    st.team = target_team
                    st.save()

            # 5. Transfer API ID if target doesn't have one
            if source_team.api_id and not target_team.api_id:
                target_team.api_id = source_team.api_id
                target_team.save()
                print(f"Transferred API ID {source_team.api_id} to {target_name}")

            # 6. Delete source team
            source_team.delete()
            print(f"Successfully merged {source_name} into {target_name}")

    except Exception as e:
        print(f"Error merging {source_name} -> {target_name}: {e}")

# Mapeamento: "Nome Longo (SofaScore)" -> "Nome Curto (StatsFut)"
MAPPINGS = [
    ("FC St. Gallen 1879", "St. Gallen"),
    ("FC Lugano", "Lugano"),
    ("FC Sion", "Sion"),
    ("FC Luzern", "Luzern"),
    ("FC Thun", "Thun"),
    ("BSC Young Boys", "Young Boys"),
    ("Grasshopper Club Zürich", "Grasshoppers"),
    ("FC Lausanne-Sport", "Lausanne"),
    ("FC Zürich", "Zurich"),
    ("FC Vaduz", "Vaduz"), # Se existir curto, senão renomeia
    ("Servette FC", "Servette"),
    ("Neuchâtel Xamax", "Xamax"),
    ("Neuchâtel Xamax FCS", "Xamax"), # Outra variação possível
    ("FC Basel 1893", "Basel"), # Importante!
    ("Yverdon-Sport FC", "Yverdon"),
    ("FC Winterthur", "Winterthur"),
    ("FC Stade-Lausanne-Ouchy", "Lausanne Ouchy"),
    ("FC Aarau", "Aarau"),
    ("FC Wil 1900", "Wil"),
    ("AC Bellinzona", "Bellinzona"),
    ("FC Schaffhausen", "Schaffhausen"),
    ("Stade Nyonnais", "Nyonnais"),
    ("FC Baden", "Baden")
]

if __name__ == "__main__":
    print("Starting Swiss Teams Merge...")
    for src, tgt in MAPPINGS:
        merge_teams(src, tgt)
    print("Done.")
