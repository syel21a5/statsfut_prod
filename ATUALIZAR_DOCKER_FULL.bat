@echo off
echo ==================================================
echo   SINCRO-BOT DOCKER (LOCAL) - STATSFUT
echo ==================================================
echo.

REM 1. Rodar o Master Fetcher (Smart Manager) via Tor dentro do Docker
echo [+] Passo 1: Buscando resultados e classificacoes (via Tor)...
docker exec -it statsfut-web-1 python master_fetcher.py --tor

REM 2. Importar os payloads gerados para o banco do Docker
echo [+] Passo 2: Importando placares e rodadas para o banco local...
docker exec -it statsfut-web-1 python manage.py import_all_leagues

REM 3. Rodar o Smart Deep Manager (Escanteios e Minutos) via Tor
echo [+] Passo 3: Buscando escanteios e detalhes dos ultimos jogos (via Tor)...
docker exec -it statsfut-web-1 python manage.py smart_deep_manager --proxy socks5://127.0.0.1:9050

REM 4. Recalcular tabelas
echo [+] Passo 4: Recalculando classificacoes e estatísticas...
docker exec -it statsfut-web-1 python manage.py recalculate_standings --all --smart

echo.
echo ==================================================
echo   CONCLUIDO! Seu Docker esta 100%% atualizado.
echo ==================================================
pause
