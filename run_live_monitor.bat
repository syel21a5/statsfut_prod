@echo off
echo Iniciando monitoramento de jogos ao vivo...
echo Intervalo: 15 minutos (para economizar creditos)
echo Pressione CTRL+C para parar.
echo.

cd /d "%~dp0"
python scripts\monitor_live_matches.py
pause