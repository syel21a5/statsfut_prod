@echo off
title StatsFut - Deep Scraper Argentina
echo ==================================================
echo      StatsFut - Atualizador Profundo (Argentina)
echo ==================================================
echo.
cd /d %~dp0

echo.
set /p use_tor="Deseja usar o Tor (s/n)? "
set TOR_FLAG=
if /i "%use_tor%"=="s" set TOR_FLAG=--tor

echo.
echo [1/4] Processando Temporada 2026...
python manage.py deep_scrape_sofascore --league_id 22 --season_year 2026 %TOR_FLAG%

echo.
echo [2/4] Processando Temporada 2025...
python manage.py deep_scrape_sofascore --league_id 22 --season_year 2025 %TOR_FLAG%

echo.
echo [3/4] Processando Temporada 2024...
python manage.py deep_scrape_sofascore --league_id 22 --season_year 2024 %TOR_FLAG%

echo.
echo [4/4] Processando Temporada 2023...
python manage.py deep_scrape_sofascore --league_id 22 --season_year 2023 %TOR_FLAG%

echo.
echo ==================================================
echo   CONCLUIDO! Seus dados locais estao atualizados.
echo ==================================================
pause
