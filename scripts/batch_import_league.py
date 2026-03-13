import os
import sys
import subprocess
import argparse
import json
from datetime import datetime

# Garante que o diretório raiz do projeto esteja no sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

def run_command(command):
    """Executa um comando no shell e exibe a saída em tempo real."""
    print(f"\n--- Executando: {command}\n")
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        rc = process.poll()
        if rc != 0:
            print(f"\n--- [ERRO] Comando falhou com código de saída {rc}: {command}")
        return rc
    except Exception as e:
        print(f"\n--- [EXCEÇÃO] Ocorreu um erro ao executar o comando: {e}")
        return -1

def get_full_start_year(year_str):
    """Converte um ano de temporada (ex: '23/24' ou '2016') para um ano inicial de 4 dígitos (ex: 2023 ou 2016)."""
    if not year_str or not isinstance(year_str, str):
        return 0
    try:
        # Handles "23/24" -> 2023 and "2016" -> 2016
        start_year_part = year_str.split('/')[0]
        start_year_short = int(start_year_part)
        return start_year_short + 2000 if start_year_short < 100 else start_year_short
    except (ValueError, IndexError):
        return 0

def main():
    parser = argparse.ArgumentParser(description="Script completo para buscar, importar, e processar uma liga inteira do SofaScore.")
    parser.add_argument("--tournament_id", type=int, required=True, help="ID do torneio no SofaScore.")
    parser.add_argument("--league_name", type=str, required=True, help="Nome da liga no banco de dados (ex: 'Super League').")
    parser.add_argument("--country", type=str, required=True, help="País da liga no banco de dados (ex: 'Suica').")
    parser.add_argument("--start_year", type=int, default=2016, help="Ano de início para a busca de temporadas históricas.")
    parser.add_argument("--file_suffix", type=str, default="l1", help="Sufixo para os arquivos TXT (ex: 'ch1').")
    parser.add_argument("--output_country_dir", type=str, help="Nome do diretório do país em historical_data (ex: 'Switzerland').")
    parser.add_argument("--output_league_dir", type=str, help="Nome do diretório da liga em historical_data (ex: 'Super-League').")
    
    args = parser.parse_args()

    # 1. Listar todas as temporadas disponíveis para o torneio
    print(">>> Passo 1: Listando temporadas disponíveis no SofaScore...")
    list_seasons_cmd = f"python proxy_sofascore_fetcher.py --tournament {args.tournament_id} --list-seasons"
    
    # Captura a saída para processar o JSON
    seasons_to_import = []
    try:
        result = subprocess.run(list_seasons_cmd, shell=True, capture_output=True, text=True, check=True, encoding='utf-8')
        seasons_data = json.loads(result.stdout)
        
        seasons_to_import = [
            s for s in seasons_data
            if get_full_start_year(s.get('year')) >= args.start_year
        ]
        print(f"Encontradas {len(seasons_to_import)} temporadas para importar desde {args.start_year}.")
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
        print(f"[ERRO] Falha ao listar ou processar as temporadas: {e}")
        print("Saída recebida:", result.stdout if 'result' in locals() else "N/A")
        return

    if not seasons_to_import:
        print("AVISO: Nenhuma temporada encontrada para os critérios fornecidos. O script será encerrado.")
        return

    # 2. Iterar sobre cada temporada para buscar e importar
    for season in sorted(seasons_to_import, key=lambda s: get_full_start_year(s['year'])):
        season_id = season['id']
        season_year_str = season['year']
        
        # O ano da temporada para o Django é o ano de término (ex: 2023/2024 -> 2024)
        start_year = get_full_start_year(season_year_str)
        end_year = start_year + 1 if '/' in season_year_str else start_year

        print(f"\n>>> Passo 2: Processando Temporada {season_year_str} (Sofa ID: {season_id}, Ano DB: {end_year})")

        # a. Fetch do payload
        fetch_cmd = f"python proxy_sofascore_fetcher.py --tournament {args.tournament_id} --season {season_id}"
        if run_command(fetch_cmd) != 0:
            print(f"[AVISO] Falha ao baixar o payload para a temporada {season_year_str}. Pulando.")
            continue

        # b. Importar o payload
        import_cmd = (
            f"python manage.py import_sofascore_payload --file payload.json "
            f"--league_name \"{args.league_name}\" --country \"{args.country}\" --season_year {end_year}"
        )
        if run_command(import_cmd) != 0:
            print(f"[AVISO] Falha ao importar os dados para a temporada {season_year_str}. Pulando.")
            continue
            
        # c. Recalcular a tabela
        recalc_cmd = f"python manage.py recalculate_standings --league_name \"{args.league_name}\" --country \"{args.country}\" --season_year {end_year}"
        run_command(recalc_cmd)

        # Exporta o TXT para a temporada recém-importada
        export_cmd = (
            f"python scripts/export_brazil_txt.py --league_name \"{args.league_name}\" --country \"{args.country}\" "
            f"--start_year {start_year} --end_year {end_year} --file_suffix {args.file_suffix} "
            f"--output_country_dir \"{args.output_country_dir or args.country}\" "
            f"--output_league_dir \"{args.output_league_dir or args.league_name}\""
        )
        run_command(export_cmd)

    # 3. Baixar todos os logos da liga
    print("\n>>> Passo 3: Baixando logos dos times...")
    # O script de logos já pega todos os times com `sofa_` ID, então não precisa de args
    download_logos_cmd = "python download_local_logos.py"
    run_command(download_logos_cmd)

    # 4. Exportar os arquivos TXT históricos
    print("\n>>> Passo 4: Exportando arquivos TXT históricos...")
    
    # O ano final para exportação é o da temporada mais recente
    latest_year = max(
        get_full_start_year(s['year']) + 1 if '/' in s['year'] else get_full_start_year(s['year']) 
        for s in seasons_to_import
    )
    
    export_cmd = (
        f"python scripts/export_brazil_txt.py --league_name \"{args.league_name}\" --country \"{args.country}\" "
        f"--start_year {args.start_year} --end_year {latest_year} --file_suffix {args.file_suffix} "
        f"--output_country_dir \"{args.output_country_dir or args.country}\" "
        f"--output_league_dir \"{args.output_league_dir or args.league_name}\""
    )
    run_command(export_cmd)
    
    print("\n--- Processo concluído com sucesso! ---")

if __name__ == "__main__":
    main()
