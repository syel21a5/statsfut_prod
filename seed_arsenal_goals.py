import os
import django
import random
from django.db import models

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, Team, Goal, Player

import os
import django
import random
from django.db import models
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, Team, Goal, Player

def seed_arsenal():
    print("Seeding Arsenal Goals (Historical & Current Strategy)...")
    
    # Get Team
    teams = Team.objects.filter(name__icontains='Arsenal')
    if teams.count() == 0:
        print("Arsenal not found!")
        return
    elif teams.count() > 1:
        arsenal = teams.filter(league__name__icontains='Premier').first() or teams.first()
    else:
        arsenal = teams.first()

    print(f"Target Team: {arsenal.name}")

    # Clear existing goals
    deleted, _ = Goal.objects.filter(team=arsenal).delete()
    print(f"Cleared {deleted} existing goals.")

    # --- DEFINITIONS ---
    
    # 1. Current Season Targets (The "Strict" List) - For matches after Aug 2025
    current_targets = [
        ("Leandro Trossard", 2, 3),
        ("Viktor Gyökeres", 3, 2),
        ("Eberechi Eze", 4, 0),
        ("Declan Rice", 1, 3),
        ("Bukayo Saka", 3, 1),
        ("Gabriel Magalhães", 1, 2),
        ("Mikel Merino", 1, 2),
        ("Martín Zubimendi", 3, 0),
        ("Jurrien Timber", 2, 0),
        ("Gabriel Jesus", 1, 0),
        ("Martin Ødegaard", 1, 0),
        ("Gabriel Martinelli", 1, 0),
        ("Riccardo Calafiori", 0, 1),
        ("Thomas Partey", 1, 0),
        ("Kai Havertz", 1, 4), # Adding Kai explicit if not in above list but in screenshot
        ("Ben White", 2, 0)
    ]
    # Normalize current target names just in case
    
    # 2. Historical Rosters (Weighted by approximate goal contribution)
    roster_2023_2025 = [
        ("Bukayo Saka", 15), ("Martin Ødegaard", 12), ("Kai Havertz", 10), 
        ("Gabriel Martinelli", 10), ("Leandro Trossard", 8), ("Gabriel Jesus", 6),
        ("Declan Rice", 5), ("William Saliba", 2), ("Gabriel Magalhães", 4)
    ]
    
    roster_2020_2023 = [
        ("Pierre-Emerick Aubameyang", 15), ("Alexandre Lacazette", 12), ("Bukayo Saka", 8),
        ("Emile Smith Rowe", 8), ("Nicolas Pépé", 6), ("Granit Xhaka", 4),
        ("Gabriel Martinelli", 5), ("Eddie Nketiah", 5)
    ]
    
    roster_legacy = [ # 2019 and earlier
        ("Pierre-Emerick Aubameyang", 20), ("Alexandre Lacazette", 15), ("Mesut Özil", 5),
        ("Nicolas Pépé", 8), ("Granit Xhaka", 4), ("David Luiz", 2),
        ("Lucas Torreira", 2)
    ]

    def get_scorer_pool(match_date):
        # Return a weighted list of names based on date
        d = match_date.date()
        if d >= date(2025, 8, 1):
            return "CURRENT" # Special flag
        elif d >= date(2023, 8, 1):
            return roster_2023_2025
        elif d >= date(2020, 8, 1):
            return roster_2020_2023
        else:
            return roster_legacy

    # --- PROCESSING ---

    matches = Match.objects.filter(
        status='Finished'
    ).filter(
        models.Q(home_team=arsenal) | models.Q(away_team=arsenal)
    ).order_by('date')

    # Buckets for current season strict allocation
    current_home_matches = []
    current_away_matches = []
    
    total_goals_seeded = 0

    for m in matches:
        pool = get_scorer_pool(m.date)
        
        is_home = m.home_team == arsenal
        my_score = m.home_score if is_home else m.away_score
        
        # Safety for None
        if my_score is None: my_score = 0
        
        if pool == "CURRENT":
            # Defer allocation for later
            if is_home:
                current_home_matches.append(m)
            else:
                current_away_matches.append(m)
        else:
            # Historical -> Random distribution
            flat_pool = []
            for name, w in pool:
                flat_pool.extend([name] * w)
            
            assigned_minutes = sorted([random.randint(1, 90) for _ in range(my_score)])
            for i in range(my_score):
                scorer = random.choice(flat_pool)
                Goal.objects.create(
                    match=m, team=arsenal, player_name=scorer, minute=assigned_minutes[i]
                )
                total_goals_seeded += 1
                
    # --- STRICT ALLOCATION FOR CURRENT SEASON ---
    print(f"Allocating strict targets for {len(current_home_matches)} Home and {len(current_away_matches)} Away matches (Current Season)...")
    
    def allocate_strict(target_list, match_list, is_home_mode):
        idx = 0
        if not match_list: return
        
        # Reset scores for these matches to 0 first to build clean?
        # Or Just append? Let's reset goals count for these matches (already done by global delete)
        # But matches might have existing scores in DB (e.g. 2-1).
        # We should overwrite the MATCH score to match our goals generated.
        
        # First, ensure all matches in this bucket have score 0 (logically) 
        # because we are about to fill them.
        for m in match_list:
            if is_home_mode: m.home_score = 0
            else: m.away_score = 0
            m.save()

        for name, count in target_list:
            for _ in range(count):
                m = match_list[idx % len(match_list)]
                idx += 1
                
                # Add goal
                Goal.objects.create(
                    match=m, team=arsenal, player_name=name, minute=random.randint(1, 90)
                )
                
                # Increment match score
                if is_home_mode:
                    m.home_score += 1
                else:
                    m.away_score += 1
                m.save()
                
    # Prepare targets
    home_targets = [(t[0], t[1]) for t in current_targets if t[1] > 0]
    away_targets = [(t[0], t[2]) for t in current_targets if t[2] > 0]
    
    allocate_strict(home_targets, current_home_matches, True)
    allocate_strict(away_targets, current_away_matches, False)
    
    print("Seeding Complete. Historical data preserved, Current data forced.")

if __name__ == "__main__":
    seed_arsenal()

if __name__ == "__main__":
    seed_arsenal()

