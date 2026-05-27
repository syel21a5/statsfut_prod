<#
.SYNOPSIS
    Exporta dados do Deep Scrape de uma liga específica do menu e envia pro servidor via GitHub.

.EXEMPLO
    .\enviar_deep_scrape_liga.ps1 -MenuNumero 2     (Libertadores)
    .\enviar_deep_scrape_liga.ps1 -MenuNumero 11    (Dinamarca)
    .\enviar_deep_scrape_liga.ps1 -MenuNumero 2 -Mensagem "Libertadores 2025-2026"
#>

param(
    [Parameter(Mandatory=$true)]
    [int]$MenuNumero,
    
    [string]$Mensagem = ""
)

$ErrorActionPreference = "Stop"
$PROJECT_DIR = "i:\GitHub\statsfut\statsfut"
$DATA_DIR = "$PROJECT_DIR\deep_scrape_exports"
$DATA_FILE = "dados_deep_scrape.json"

# ==========================================
# NUMERAÇÃO EXATA DO MENU DO DEEP SCRAPE
# ==========================================
$LIGAS = @{
    1  = "Alemanha - Bundesliga"
    2  = "America do Sul - Copa Libertadores"
    3  = "America do Sul - Copa Sul-Americana"
    4  = "Argentina - Liga Profesional"
    5  = "Australia - A-League Men"
    6  = "Austria - Bundesliga"
    7  = "Belgica - Pro League"
    8  = "Brasil - Brasileirão"
    9  = "Chile - Primera Division"
    10 = "Colombia - Primera A"
    11 = "Dinamarca - Superliga"
    12 = "Equador - Liga Pro"
    13 = "Espanha - La Liga"
    14 = "Estados Unidos - MLS"
    15 = "Finlandia - Veikkausliiga"
    16 = "Franca - Ligue 1"
    17 = "Grecia - Super League"
    18 = "Holanda - Eredivisie"
    19 = "Inglaterra - Championship"
    20 = "Islandia - Besta deild karla"
    21 = "Italia - Serie A"
    22 = "Japao - J1 League"
    23 = "Mexico - Liga MX"
    24 = "Noruega - Eliteserien"
    25 = "Paraguai - Primera Division"
    26 = "Peru - Liga 1"
    27 = "Polonia - Ekstraklasa"
    28 = "Portugal - Primeira Liga"
    29 = "Russia - Premier Liga"
    30 = "Suecia - Allsvenskan"
    31 = "Suica - Super League"
    32 = "Turquia - Süper Lig"
    33 = "Ucrania - Premier League"
    34 = "Uruguai - Primera Division"
    35 = "Inglaterra - Premier League"
    36 = "Escocia - Premiership"
}

# Mapeamento: Número do Menu -> ID do banco de dados
$MENU_PARA_BANCO = @{
    1  = 7    # Alemanha - Bundesliga
    2  = 51   # America do Sul - Copa Libertadores
    3  = 53   # America do Sul - Copa Sul-Americana
    4  = 22   # Argentina - Liga Profesional
    5  = 21   # Australia - A-League Men
    6  = 44   # Austria - Bundesliga
    7  = 10   # Belgica - Pro League
    8  = 2    # Brasil - Brasileirão
    9  = 31   # Chile - Primera Division
    10 = 30   # Colombia - Primera A
    11 = 15   # Dinamarca - Superliga
    12 = 60   # Equador - Liga Pro
    13 = 4    # Espanha - La Liga
    14 = 35   # Estados Unidos - MLS
    15 = 16   # Finlandia - Veikkausliiga
    16 = 8    # Franca - Ligue 1
    17 = 17   # Grecia - Super League
    18 = 9    # Holanda - Eredivisie
    19 = 50   # Inglaterra - Championship
    20 = 59   # Islandia - Besta deild karla
    21 = 6    # Italia - Serie A
    22 = 18   # Japao - J1 League
    23 = 32   # Mexico - Liga MX
    24 = 14   # Noruega - Eliteserien
    25 = 58   # Paraguai - Primera Division
    26 = 61   # Peru - Liga 1
    27 = 26   # Polonia - Ekstraklasa
    28 = 34   # Portugal - Primeira Liga
    29 = 46   # Russia - Premier Liga
    30 = 13   # Suecia - Allsvenskan
    31 = 40   # Suica - Super League
    32 = 36   # Turquia - Süper Lig
    33 = 49   # Ucrania - Premier League
    34 = 57   # Uruguai - Primera Division
    35 = 43   # Inglaterra - Premier League
    36 = 27   # Escocia - Premiership
}

# Validação
if (-not $LIGAS.ContainsKey($MenuNumero)) {
    Write-Host "❌ Número inválido! Use um número entre 1 e 36 do menu do Deep Scrape." -ForegroundColor Red
    exit 1
}

$nomeLiga = $LIGAS[$MenuNumero]
$bancoID = $MENU_PARA_BANCO[$MenuNumero]

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  ENVIAR DEEP SCRAPE PARA O SERVIDOR" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Menu #$MenuNumero -> $nomeLiga (ID banco: $bancoID)" -ForegroundColor White
Write-Host ""

# 1. Exporta a liga específica
Write-Host "[1/3] Exportando dados do Docker..." -ForegroundColor Yellow
Set-Location $PROJECT_DIR

try {
    docker compose exec web mkdir -p /app/deep_scrape_exports 2>$null
    docker compose exec web python manage.py export_deep_scrape --liga $bancoID --output /app/deep_scrape_exports/$DATA_FILE
    
    if (-not (Test-Path $DATA_DIR)) {
        New-Item -ItemType Directory -Path $DATA_DIR -Force | Out-Null
    }
    
    docker compose cp "web:/app/deep_scrape_exports/$DATA_FILE" "$DATA_DIR\$DATA_FILE"
    
    Write-Host "  OK!" -ForegroundColor Green
} catch {
    Write-Host "  Erro na exportacao: $_" -ForegroundColor Red
    exit 1
}

# 2. Verifica o arquivo
Write-Host ""
Write-Host "[2/3] Verificando dados..." -ForegroundColor Yellow

$fileInfo = Get-Item "$DATA_DIR\$DATA_FILE"
$fileSizeKB = [math]::Round($fileInfo.Length / 1KB, 1)

$jsonContent = Get-Content "$DATA_DIR\$DATA_FILE" -Raw | ConvertFrom-Json
$totalPartidas = $jsonContent.Count
$totalGols = 0
foreach ($item in $jsonContent) { $totalGols += $item.goals.Count }

Write-Host "  $totalPartidas partidas, $totalGols gols" -ForegroundColor Green
Write-Host "  $fileSizeKB KB" -ForegroundColor Green

# 3. Commit e push
Write-Host ""
Write-Host "[3/3] Enviando para o GitHub..." -ForegroundColor Yellow

$dataAtual = Get-Date -Format "dd/MM/yyyy HH:mm"
if ($Mensagem -eq "") {
    $Mensagem = "Deep Scrape: $nomeLiga - $dataAtual"
}

try {
    git add "deep_scrape_exports/$DATA_FILE"
    
    $status = git status --porcelain
    if ($status) {
        git commit -m "$Mensagem"
        git push origin main
        Write-Host "  Enviado para o GitHub!" -ForegroundColor Green
    } else {
        Write-Host "  Nada novo" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Erro no git: $_" -ForegroundColor Red
    exit 1
}

# 4. Instrucoes pro servidor
Write-Host ""
Write-Host "PRONTO! Agora no SERVIDOR:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  cd /www/wwwroot/statsfut.com" -ForegroundColor Yellow
Write-Host "  git pull origin main" -ForegroundColor Yellow
Write-Host "  source venv/bin/activate" -ForegroundColor Yellow
Write-Host "  python manage.py import_deep_scrape deep_scrape_exports/dados_deep_scrape.json" -ForegroundColor Yellow
Write-Host "  python manage.py recalculate_standings --all --smart" -ForegroundColor Yellow
Write-Host ""
