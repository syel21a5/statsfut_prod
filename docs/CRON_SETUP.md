# Cron Configuration for StatsFut

## Setup Instructions

1. **Edit crontab on the server:**
   ```bash
   crontab -e
   ```

2. **Add these lines:**
   ```bash
   # Update football data daily at 3 AM (after football-data.co.uk updates)
   0 3 * * * /www/wwwroot/statsfut.com/scripts/update_data.sh >> /www/wwwroot/statsfut.com/logs/cron.log 2>&1
   
   # Update live matches every hour during match days (Friday-Monday)
   0 * * * 5-1 cd /www/wwwroot/statsfut.com && /www/wwwroot/statsfut.com/venv/bin/python manage.py update_live_matches --mode both >> /www/wwwroot/statsfut.com/logs/live_updates.log 2>&1
   ```

3. **Verify cron is running:**
   ```bash
   crontab -l
   ```

## What Each Cron Does

### Daily Full Update (3 AM)
- Downloads CSV data from football-data.co.uk (free, historical data)
- Updates live matches and upcoming fixtures via API
- Normalizes team names
- Removes duplicates
- Recalculates standings
- **Runs:** Every day at 3 AM

### Hourly Live Updates (Match Days)
- Fetches live match scores
- Updates upcoming fixtures (next 14 days)
- **Runs:** Every hour on Friday through Monday (when most matches happen)

## Manual Execution

To run updates manually:

```bash
# Full update (CSV + API + cleanup)
cd /www/wwwroot/statsfut.com
./scripts/update_data.sh

# Just live matches
cd /www/wwwroot/statsfut.com
source venv/bin/activate
python manage.py update_live_matches --mode both
```

## Logs

- Full updates: `/www/wwwroot/statsfut.com/logs/update.log`
- Cron execution: `/www/wwwroot/statsfut.com/logs/cron.log`
- Live updates: `/www/wwwroot/statsfut.com/logs/live_updates.log`
