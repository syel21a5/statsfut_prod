import os
import django
import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Match, Team, Season
from django.db.models import Count, Q

def run():
    # Find Austria Bundesliga
    league = League.objects.filter(name__icontains="Bundesliga", country="Austria").first()
    if not league:
        # Fallback
        league = League.objects.filter(name="Bundesliga", country="Austria").first()
    
    if not league:
        print("Liga da Áustria não encontrada.")
        return

    print(f"Buscando duplicatas na liga: {league.name} ({league.country})")

    # 1. Exact Duplicates (Same Date, Home, Away)
    # ------------------------------------------------
    print("\n--- Verificando duplicatas exatas (mesma data) ---")
    # Check ALL matches, not just latest season
    matches = Match.objects.filter(league=league).order_by('date')
    
    seen_matches = {}
    duplicates_exact = 0
    deleted_exact = 0

    for match in matches:
        if not match.date:
             continue
             
        match_date = match.date.strftime('%Y-%m-%d')
        key = (match_date, match.home_team_id, match.away_team_id)
        
        if key in seen_matches:
            seen_matches[key].append(match)
        else:
            seen_matches[key] = [match]

    for key, match_list in seen_matches.items():
        if len(match_list) > 1:
            duplicates_exact += 1
            home_team = match_list[0].home_team.name
            away_team = match_list[0].away_team.name
            date_str = key[0]
            
            print(f"Duplicata Exata ({len(match_list)}x): {home_team} vs {away_team} em {date_str}")
            
            # Sort: Finished first, then ID (lower=older)
            match_list.sort(key=lambda m: (m.status != 'Finished', m.id))
            
            keeper = match_list[0]
            to_delete = match_list[1:]
            
            print(f"  Mantendo ID: {keeper.id} (Status: {keeper.status}, Score: {keeper.home_score}-{keeper.away_score})")
            
            for d in to_delete:
                print(f"  Deletando ID: {d.id}")
                d.delete()
                deleted_exact += 1

    # 2. Year Shift Duplicates (Same Day/Month, Home, Away, Score, but diff Year)
    # ------------------------------------------------
    print("\n--- Verificando duplicatas de ano incorreto (Year Shift) ---")
    # Refresh matches list
    matches = Match.objects.filter(league=league).order_by('date')
    
    seen_shifted = {}
    duplicates_shifted = 0
    deleted_shifted = 0
    
    for match in matches:
        if not match.date:
             continue
        
        # Key: (Month, Day, Home, Away, HomeScore, AwayScore)
        # We ignore Year here
        day = match.date.day
        month = match.date.month
        
        # Use score as part of key to avoid false positives (e.g. played twice on same day in diff years with diff scores? unlikely but safer)
        # But score might be None for scheduled matches.
        h_score = match.home_score if match.home_score is not None else -1
        a_score = match.away_score if match.away_score is not None else -1
        
        key = (month, day, match.home_team_id, match.away_team_id, h_score, a_score)
        
        if key in seen_shifted:
            seen_shifted[key].append(match)
        else:
            seen_shifted[key] = [match]
            
    for key, match_list in seen_shifted.items():
        if len(match_list) > 1:
            # Check if years differ
            years = set(m.date.year for m in match_list)
            if len(years) > 1:
                duplicates_shifted += 1
                home_team = match_list[0].home_team.name
                away_team = match_list[0].away_team.name
                date_str = f"{key[1]}/{key[0]}" # Day/Month
                
                print(f"Duplicata de Ano ({len(match_list)}x): {home_team} vs {away_team} em {date_str} (Anos: {years})")
                
                # Logic: Keep the one closest to current season year
                # Season 2026 -> Valid years usually 2025, 2026.
                # If we have 2025 and 2026, keep 2026?
                # Actually, for "Year Shift" bug, the match is usually shifted by -1 year.
                # So the LATEST year is usually correct.
                
                match_list.sort(key=lambda m: m.date.year, reverse=True) # Descending year (2026, 2025)
                
                keeper = match_list[0]
                to_delete = match_list[1:]
                
                print(f"  Mantendo ID: {keeper.id} (Ano: {keeper.date.year}, Status: {keeper.status})")
                
                for d in to_delete:
                    print(f"  Deletando ID: {d.id} (Ano: {d.date.year}, Status: {d.status})")
                    d.delete()
                    deleted_shifted += 1

    print(f"\nResumo:")
    print(f"Duplicatas Exatas: {duplicates_exact} grupos, {deleted_exact} deletados")
    print(f"Duplicatas de Ano: {duplicates_shifted} grupos, {deleted_shifted} deletados")
    print(f"Total deletados: {deleted_exact + deleted_shifted}")

if __name__ == "__main__":
    run()
