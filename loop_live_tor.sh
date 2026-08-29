#!/bin/bash
# Loop do Live Radar via Tor — PRODUÇÃO (statsfut.com)
cd /www/wwwroot/statsfut.com || exit 1
while true; do
  venv/bin/python manage.py update_live_matches --mode live --force >> /www/wwwroot/statsfut.com/logs/live_tor.log 2>&1
  sleep 60
done
