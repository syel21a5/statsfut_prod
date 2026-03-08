import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match

def purge():
    league = League.objects.filter(name='Bundesliga', country='Austria').first()
    if not league:
        print("Austria league not found.")
        return

    teams = Team.objects.filter(league=league)
    count_deleted = 0
    
    for team in teams:
        name = team.name
        is_garbage = False
        
        if " v " in name:
            is_garbage = True
        elif re.match(r"^\(\d+-\d+\)$", name):
            is_garbage = True
        elif "-" in name and any(c.isdigit() for c in name):
            if "(" in name or ")" in name:
                 is_garbage = True
        elif "  v  " in name:
            is_garbage = True
        elif "           v " in name:
            is_garbage = True

        if is_garbage:
            print(f"Deleting ghost team: {name}")
            team.delete()
            count_deleted += 1

    print(f"Purged {count_deleted} ghost teams.")

if __name__ == "__main__":
    purge()
