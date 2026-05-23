@echo off
title StatsFut - Atualizar Liga no Docker (via Tor/API)
echo ==================================================
echo   ATUALIZAR LIGA NO DOCKER (LOCAL)
echo   Baixa partidas, resultados e classificacoes
echo ==================================================
echo.

cd /d %~dp0

REM ==========================================
REM MENU IGUAL AO DEEP_SCRAPE_LIGA.bat
REM ==========================================
echo Escolha a liga para ATUALIZAR:
echo.
echo   1  - Alemanha - Bundesliga
echo   2  - America do Sul - Copa Libertadores
echo   3  - America do Sul - Copa Sul-Americana
echo   4  - Argentina - Liga Profesional
echo   5  - Australia - A-League Men
echo   6  - Austria - Bundesliga
echo   7  - Belgica - Pro League
echo   8  - Brasil - Brasileirao
echo   9  - Chile - Primera Division
echo   10 - Colombia - Primera A
echo   11 - Dinamarca - Superliga
echo   12 - Equador - Liga Pro
echo   13 - Espanha - La Liga
echo   14 - Estados Unidos - MLS
echo   15 - Finlandia - Veikkausliiga
echo   16 - Franca - Ligue 1
echo   17 - Grecia - Super League
echo   18 - Holanda - Eredivisie
echo   19 - Inglaterra - Championship
echo   20 - Islandia - Besta deild karla
echo   21 - Italia - Serie A
echo   22 - Japao - J1 League
echo   23 - Mexico - Liga MX
echo   24 - Noruega - Eliteserien
echo   25 - Paraguai - Primera Division
echo   26 - Peru - Liga 1
echo   27 - Polonia - Ekstraklasa
echo   28 - Portugal - Primeira Liga
echo   29 - Russia - Premier Liga
echo   30 - Suecia - Allsvenskan
echo   31 - Suica - Super League
echo   32 - Turquia - Super Lig
echo   33 - Ucrania - Premier League
echo   34 - Uruguai - Primera Division
echo.
echo   0  - ATUALIZAR TODAS as ligas
echo.

set /p choice="Digite o numero: "

REM Mapeamento: numero do menu -> chave do tor_league_updater
REM As ligas principais usam o master_fetcher (que baixa tudo), 
REM as secundarias (Libertadores, Sul-Americana, Championship) usam tor_league_updater
if "%choice%"=="2" set LEAGUE_KEY=libertadores & goto :run_update
if "%choice%"=="3" set LEAGUE_KEY=sudamericana & goto :run_update
if "%choice%"=="19" set LEAGUE_KEY=championship & goto :run_update

REM Para as demais ligas, usar sync_all_fixtures (que baixa resultados recentes)
REM Pula o tor_league_updater e vai direto pro master_fetcher com filtro
if "%choice%"=="1" set LEAGUE_NAME=Bundesliga & set LEAGUE_COUNTRY=Alemanha & goto :run_master
if "%choice%"=="4" set LEAGUE_NAME=Liga Profesional & set LEAGUE_COUNTRY=Argentina & goto :run_master
if "%choice%"=="5" set LEAGUE_NAME=A-League & set LEAGUE_COUNTRY=Australia & goto :run_master
if "%choice%"=="6" set LEAGUE_NAME=Bundesliga & set LEAGUE_COUNTRY=Austria & goto :run_master
if "%choice%"=="7" set LEAGUE_NAME=Pro League & set LEAGUE_COUNTRY=Belgica & goto :run_master
if "%choice%"=="8" set LEAGUE_NAME=Brasileirao & set LEAGUE_COUNTRY=Brasil & goto :run_master
if "%choice%"=="9" set LEAGUE_NAME=Primera Division & set LEAGUE_COUNTRY=Chile & goto :run_master
if "%choice%"=="10" set LEAGUE_NAME=Primera A & set LEAGUE_COUNTRY=Colombia & goto :run_master
if "%choice%"=="11" set LEAGUE_NAME=Superliga & set LEAGUE_COUNTRY=Dinamarca & goto :run_master
if "%choice%"=="12" set LEAGUE_NAME=Liga Pro & set LEAGUE_COUNTRY=Equador & goto :run_master
if "%choice%"=="13" set LEAGUE_NAME=La Liga & set LEAGUE_COUNTRY=Espanha & goto :run_master
if "%choice%"=="14" set LEAGUE_NAME=MLS & set LEAGUE_COUNTRY=Estados Unidos & goto :run_master
if "%choice%"=="15" set LEAGUE_NAME=Veikkausliiga & set LEAGUE_COUNTRY=Finlandia & goto :run_master
if "%choice%"=="16" set LEAGUE_NAME=Ligue 1 & set LEAGUE_COUNTRY=Franca & goto :run_master
if "%choice%"=="17" set LEAGUE_NAME=Super League & set LEAGUE_COUNTRY=Grecia & goto :run_master
if "%choice%"=="18" set LEAGUE_NAME=Eredivisie & set LEAGUE_COUNTRY=Holanda & goto :run_master
if "%choice%"=="20" set LEAGUE_NAME=Besta deild karla & set LEAGUE_COUNTRY=Islandia & goto :run_master
if "%choice%"=="21" set LEAGUE_NAME=Serie A & set LEAGUE_COUNTRY=Italia & goto :run_master
if "%choice%"=="22" set LEAGUE_NAME=J1 League & set LEAGUE_COUNTRY=Japao & goto :run_master
if "%choice%"=="23" set LEAGUE_NAME=Liga MX & set LEAGUE_COUNTRY=Mexico & goto :run_master
if "%choice%"=="24" set LEAGUE_NAME=Eliteserien & set LEAGUE_COUNTRY=Noruega & goto :run_master
if "%choice%"=="25" set LEAGUE_NAME=Primera Division & set LEAGUE_COUNTRY=Paraguai & goto :run_master
if "%choice%"=="26" set LEAGUE_NAME=Liga 1 & set LEAGUE_COUNTRY=Peru & goto :run_master
if "%choice%"=="27" set LEAGUE_NAME=Ekstraklasa & set LEAGUE_COUNTRY=Polonia & goto :run_master
if "%choice%"=="28" set LEAGUE_NAME=Primeira Liga & set LEAGUE_COUNTRY=Portugal & goto :run_master
if "%choice%"=="29" set LEAGUE_NAME=Premier Liga & set LEAGUE_COUNTRY=Russia & goto :run_master
if "%choice%"=="30" set LEAGUE_NAME=Allsvenskan & set LEAGUE_COUNTRY=Suecia & goto :run_master
if "%choice%"=="31" set LEAGUE_NAME=Super League & set LEAGUE_COUNTRY=Suica & goto :run_master
if "%choice%"=="32" set LEAGUE_NAME=Super Lig & set LEAGUE_COUNTRY=Turquia & goto :run_master
if "%choice%"=="33" set LEAGUE_NAME=Premier League & set LEAGUE_COUNTRY=Ucrania & goto :run_master
if "%choice%"=="34" set LEAGUE_NAME=Primera Division & set LEAGUE_COUNTRY=Uruguai & goto :run_master

if "%choice%"=="0" goto :run_all

echo Opcao invalida!
pause
exit /b

:run_update
echo.
echo ==================================================
echo   ATUALIZANDO via tor_league_updater...
echo ==================================================
docker compose exec web python manage.py tor_league_updater --league %LEAGUE_KEY% --proxy none --full-scan
goto :fim

:run_master
echo.
echo ==================================================
echo   ATUALIZANDO %LEAGUE_NAME% (%LEAGUE_COUNTRY%)...
echo ==================================================

REM Para ligas principais, usa o master_fetcher
docker compose exec web python master_fetcher.py --league "%LEAGUE_NAME%" --country "%LEAGUE_COUNTRY%"
docker compose exec web python manage.py import_sofascore_payload --file "payload_temp.json" --league-name "%LEAGUE_NAME%" --country "%LEAGUE_COUNTRY%" --season-year 2026
goto :fim

:run_all
echo.
echo ==================================================
echo   ATUALIZANDO TODAS AS LIGAS...
echo ==================================================

REM Ligas secundarias
docker compose exec web python manage.py tor_league_updater --league libertadores --proxy none --full-scan
docker compose exec web python manage.py tor_league_updater --league sudamericana --proxy none --full-scan
docker compose exec web python manage.py tor_league_updater --league championship --proxy none --full-scan

REM Ligas principais (master_fetcher baixa tudo)
docker compose exec web python master_fetcher.py --tor
docker compose exec web python manage.py import_all_leagues

goto :fim

:fim
echo.
echo ==================================================
echo   CONCLUIDO! Agora rode o DEEP_SCRAPE_LIGA.bat
echo   para baixar escanteios, cartaos e gols.
echo ==================================================
pause
