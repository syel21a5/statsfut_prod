@echo off
title StatsFut - Deep Scrape por Liga (via Docker + Tor)
echo ==================================================
echo   DEEP SCRAPE - Escanteios, Cartoes, Gols
echo   Temporada Atual + Anterior
echo   (Executando dentro do Docker com Tor integrado)
echo ==================================================
echo.
cd /d %~dp0

echo Verificando se o Docker esta rodando...
docker compose ps >nul 2>&1
if errorlevel 1 (
    echo [ERRO] O Docker nao esta rodando ou os containers nao estao ativos.
    echo Por favor, inicie o Docker Desktop e rode: docker compose up -d
    pause
    exit /b 1
)

echo Garantindo que o Tor esta ativo dentro do container...
docker compose exec web sh -c "service tor start 2>/dev/null || (tor &) 2>/dev/null; sleep 2; echo 'Tor OK'"

echo.
echo Iniciando o Deep Scrape com Tor dentro do Docker...
echo.
docker compose exec web python manage.py deep_scrape_menu --tor

echo.
echo ==================================================
echo   CONCLUIDO!
echo ==================================================
pause
