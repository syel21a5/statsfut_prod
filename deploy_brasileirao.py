import os
import subprocess
import sys

def run_command(command):
    print(f"Running: {command}")
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        sys.exit(1)

def main():
    print("=== Starting Brasileirão Deploy for Production ===")
    
    # 1. Pull latest code
    print("\n[1/3] Pulling latest code from GitHub...")
    run_command("git pull origin main")
    
    # 2. Import Data (2012-2026)
    print("\n[2/3] Importing Football Data (Brasileirão 2012-2026)...")
    # We use a lower level loop to ensure coverage or just one command if the script handles it.
    # import_football_data with --min_year should handle it if logic allows, 
    # but to be safe and ensure specific focus on Brazil, let's iterate or use strict flags.
    # The updated import_football_data.py handles "League" column correctly now.
    
    # We can run for the whole range. 
    # The command 'import_football_data' with --min_year 2012 will try to fetch ALL leagues.
    # If we want ONLY Brasileirão, we should add a --league argument if supported, 
    # or just run it generally if that's the desired behavior for "prod".
    # Assuming we want to update EVERYTHING including Brasileirão:
    run_command(f"{sys.executable} manage.py import_football_data --min_year 2012")

    # 3. Recalculate Standings (2012-2026)
    print("\n[3/3] Recalculating Standings for Brasileirão...")
    for year in range(2012, 2027):
        print(f" -> Processing {year}...")
        # Using || true equivalent in python (try/except) for recalculate in case of empty years
        try:
             subprocess.run(
                [sys.executable, "manage.py", "recalculate_standings", 
                 "--league_name", "Brasileirao", 
                 "--season_year", str(year)], 
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"   ! Could not calculate for {year} (maybe no matches yet or verified empty). Continuing...")

    print("\n=== Deploy Complete! ===")
    print("Brasileirão data from 2012 to 2026 should be live.")

if __name__ == "__main__":
    main()
