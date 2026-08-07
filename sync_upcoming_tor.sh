#!/bin/bash
# Sync de jogos futuros via Tor — AMBIENTE DE TESTE (statsfut2)
# Busca os próximos 3 dias de jogos das ligas monitoradas no SofaScore (via Tor)
# e cria/atualiza no banco. Roda a cada 6h via crontab.
cd /www/wwwroot/statsfut2.statsfut.com || exit 1
LOG=logs/upcoming_tor.log
echo "===== $(date '+%Y-%m-%d %H:%M:%S') — Sync upcoming via Tor =====" >> "$LOG"
venv/bin/python manage.py shell -c "
from matches.management.commands.update_live_matches import Command as ULM
from matches.services.sofascore_tor import SofaScoreTorService
import io

cmd = ULM()
cmd.stdout = io.StringIO()
print('Buscando próximos 45 dias via Tor...')
fx = SofaScoreTorService().get_upcoming_fixtures(days_ahead=45)
print(f'Fixtures encontradas: {len(fx)}')
if fx:
    cmd.process_fixtures(fx, is_live=False, readonly_structure=False)
    out = cmd.stdout.getvalue()
    novas = sum(1 for l in out.splitlines() if '➕ Novo' in l)
    upd = sum(1 for l in out.splitlines() if '🔄 Atualizado' in l)
    print(f'Novas: {novas} | Atualizadas: {upd}')
" >> "$LOG" 2>&1
echo "===== FIM $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG"
