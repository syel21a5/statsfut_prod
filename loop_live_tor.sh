#!/bin/bash
# Loop do Live Radar via Tor — AMBIENTE DE TESTE (statsfut2)
# Roda o update_live_matches (live + rich data) a cada 60s
cd /www/wwwroot/statsfut2.statsfut.com || exit 1
while true; do
  venv/bin/python manage.py update_live_matches --mode live --force >> /www/wwwroot/statsfut2.statsfut.com/logs/live_tor.log 2>&1
  sleep 60
done
