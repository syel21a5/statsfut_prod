#!/bin/bash
# Loop do Live Radar via Tor — PRODUÇÃO (statsfut.com)
# Atualizado: Tor com NEWNYM a cada rotação + fallback direto
cd /www/wwwroot/statsfut.com || exit 1
while true; do
  # Rotacionar circuito Tor antes de cada tentativa
  printf 'AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT\r\n' | nc 127.0.0.1 9051 2>/dev/null
  sleep 3
  venv/bin/python manage.py update_live_matches --mode live --force >> /www/wwwroot/statsfut.com/logs/live_tor.log 2>&1
  sleep 120
done