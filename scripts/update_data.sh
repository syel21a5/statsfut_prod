#!/bin/bash

# Get project root directory (assuming script is in /scripts)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/update.log"

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Navigate to project root
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists in 'venv' or '.venv' inside project
# Adjust this line if your venv is located elsewhere on the server
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "========================================" >> "$LOG_FILE"
echo "Starting update at $(date)" >> "$LOG_FILE"

# 1. Update historical data (CSV) - focused on current/recent seasons
# This is FREE (uses CSV downloads), so we can run it always.
echo "Running import_football_data..." >> "$LOG_FILE"
python manage.py import_football_data --min_year 2025 >> "$LOG_FILE" 2>&1

# 2. Update live matches and upcoming fixtures (API)
# Only run this if explicitly requested with --api flag OR during live match hours (e.g., weekends)
# to save API calls on free tier.
RUN_API=false

# Check for --api argument
if [[ "$1" == "--api" ]]; then
    RUN_API=true
fi

# OPTIONAL: Uncomment below to automatically run API only on weekends (Fri-Sun)
# DOW=$(date +%u)
# if [ "$DOW" -ge 5 ]; then
#    RUN_API=true
# fi

if [ "$RUN_API" = true ]; then
    echo "Running update_live_matches (API)..." >> "$LOG_FILE"
    python manage.py update_live_matches >> "$LOG_FILE" 2>&1
else
    echo "Skipping update_live_matches (API) to save quota. Pass --api to force run." >> "$LOG_FILE"
fi

# 3. Fix Match Statuses (Ensure matches with scores are marked as Finished)
echo "Fixing match statuses..." >> "$LOG_FILE"
python manage.py fix_match_status >> "$LOG_FILE" 2>&1

# 4. Normalize Teams (Merge duplicate teams like Wolves/Wolverhampton)
echo "Normalizing teams..." >> "$LOG_FILE"
python manage.py normalize_teams --league_name "Premier League" >> "$LOG_FILE" 2>&1

# 5. Remove Match Duplicates (Safety net for duplicate games)
echo "Removing duplicate matches..." >> "$LOG_FILE"
python manage.py remove_match_duplicates >> "$LOG_FILE" 2>&1

# 6. Recalculate Standings (CRITICAL: Tables won't update without this)
echo "Recalculating standings..." >> "$LOG_FILE"
python manage.py recalculate_standings --league_name "Premier League" >> "$LOG_FILE" 2>&1

echo "Update finished at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
