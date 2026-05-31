@echo off
echo ==================================================
echo   SINCRO-BOT DOCKER (TEMPORADA COMPLETA) - STATSFUT
echo ==================================================
echo.
echo Este script fara uma varredura COMPLETA de todos os jogos
echo da temporada atual de todas as ligas (evitando buracos no historico).
echo.

cd /d "%~dp0"

echo [+] Passo 0: Verificando e iniciando containers do Docker...
docker compose up -d

echo [+] Passo 0.5: Garantindo que o Tor esta ativo e pronto dentro do container...
docker compose exec web sh -c "service tor start 2>/dev/null || (tor &) 2>/dev/null"
echo Aguardando 5 segundos para o circuito do Tor se estabelecer...
timeout /t 5 >nul

REM 1. Rodar o Master Fetcher (Smart Manager) via Tor dentro do Docker no modo Full Scan e Interativo
echo [+] Passo 1: Selecione as ligas e buscando jogos (via Tor)...
docker compose exec -it web python master_fetcher.py --tor --full-scan --interactive

REM 2. Importar os payloads gerados para o banco do Docker
echo [+] Passo 2: Importando placares e rodadas para o banco local...
docker compose exec -it web python manage.py import_all_leagues

REM 3. Rodar o Smart Deep Manager (Escanteios e Minutos) via Tor
echo [+] Passo 3: Buscando detalhes de escanteios e estatisticas (via Tor)...
docker compose exec -it web python manage.py smart_deep_manager --proxy socks5://127.0.0.1:9050

REM 4. Recalcular tabelas
echo [+] Passo 4: Recalculando classificacoes e estatisticas...
docker compose exec -it web python manage.py recalculate_standings --all --smart

echo.
echo ==================================================
echo   CONCLUIDO! A temporada atual esta 100%% atualizada.
echo ==================================================
pause
