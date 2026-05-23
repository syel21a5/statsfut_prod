@echo off
title StatsFut - Deep Scrape por Liga (Universal)
echo ==================================================
echo   DEEP SCRAPE - Escanteios, Cartoes, Gols
echo   Temporada Atual + Anterior
echo ==================================================
echo.
cd /d %~dp0

echo Deseja usar o Tor? (Recomendado para evitar bloqueios)
set /p use_tor="Usar Tor (s/n)? "
set TOR_FLAG=
if /i "%use_tor%"=="s" set TOR_FLAG=--tor

echo.
python manage.py deep_scrape_menu %TOR_FLAG%

echo.
echo ==================================================
echo   CONCLUIDO!
echo ==================================================
pause
