@echo off
echo ==================================================
echo   SINCRO-BOT DOCKER (TEMPORADA COMPLETA) - STATSFUT
echo ==================================================
echo.
echo Este script fara uma varredura COMPLETA de todos os jogos
echo da temporada atual de todas as ligas (evitando buracos no historico).
echo.

REM 1. Rodar o Master Fetcher (Smart Manager) via Tor dentro do Docker no modo Full Scan e Interativo
echo [+] Passo 1: Selecione as ligas e buscando jogos (via Tor)...
docker exec -it statsfut-web-1 python master_fetcher.py --tor --full-scan --interactive

REM 2. Importar os payloads gerados para o banco do Docker
echo [+] Passo 2: Importando placares e rodadas para o banco local...
docker exec -it statsfut-web-1 python manage.py import_all_leagues

REM 3. Rodar o Smart Deep Manager (Escanteios e Minutos) via Tor
echo [+] Passo 3: Buscando detalhes de escanteios e estatisticas (via Tor)...
docker exec -it statsfut-web-1 python manage.py smart_deep_manager --proxy socks5://127.0.0.1:9050

REM 4. Recalcular tabelas
echo [+] Passo 4: Recalculando classificacoes e estatisticas...
docker exec -it statsfut-web-1 python manage.py recalculate_standings --all --smart

echo.
echo ==================================================
echo   CONCLUIDO! A temporada atual esta 100%% atualizada.
echo ==================================================
pause
