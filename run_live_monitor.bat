@echo off
echo Iniciando monitoramento de jogos ao vivo...
echo Intervalo: 15 minutos (para economizar creditos)
echo Pressione CTRL+C para parar.
echo.

cd /d "%~dp0"

set PYTHON_EXEC=python
if exist venv\Scripts\python.exe (
    set PYTHON_EXEC=venv\Scripts\python.exe
)

%PYTHON_EXEC% scripts\monitor_live_matches.py
pause