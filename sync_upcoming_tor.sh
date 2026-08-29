#!/bin/bash
# Sync de jogos futuros via Tor — PRODUÇÃO (statsfut.com)
cd /www/wwwroot/statsfut.com || exit 1
LOG=logs/upcoming_tor.log
echo "===== $(date '+%Y-%m-%d %H:%M:%S') — Sync upcoming via Tor =====" >> "$LOG"
venv/bin/python manage.py shell -c "
from matches.management.commands.update_live_matches import Command as ULM
from matches.services.sofascore_tor import SofaScoreTorService
import io
cmd = ULM(); cmd.stdout = io.StringIO()
print('Buscando próximos 45 dias via Tor...')
fx = SofaScoreTorService().get_upcoming_fixtures(days_ahead=45)
print(f'Fixtures: {len(fx)}')
if fx:
    cmd.process_fixtures(fx, is_live=False, readonly_structure=False)
" >> "$LOG" 2>&1
echo "===== FIM =====" >> "$LOG"
