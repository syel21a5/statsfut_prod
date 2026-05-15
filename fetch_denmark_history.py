import os
import subprocess
import time

seasons = {
    2021: 29247,
    2022: 36834,
    2023: 41914,
    2024: 52172,
    2025: 61326,
    2026: 76491
}

output_dir = "historical_data/Denmark/Superliga"
os.makedirs(output_dir, exist_ok=True)

for year, season_id in seasons.items():
    print(f"--- Fetching Denmark Superliga {year} (ID: {season_id}) ---")
    filename = f"{year}.json"
    filepath = os.path.join(output_dir, filename)
    
    if os.path.exists(filepath):
        print(f"Skipping {year}, file already exists.")
        continue

    # Run fetcher
    cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "39", "--season", str(season_id)]
    subprocess.run(cmd)
    
    # Rename payload.json to the target filepath
    if os.path.exists("payload.json"):
        if os.path.exists(filepath):
            os.remove(filepath)
        os.rename("payload.json", filepath)
        print(f"Saved {filepath}")
    else:
        print(f"Failed to fetch {year}")
    
    time.sleep(2) # Extra safety
