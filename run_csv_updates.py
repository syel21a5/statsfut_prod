import time
import subprocess
import schedule
import logging
from datetime import datetime

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("csv_update.log"),
        logging.StreamHandler()
    ]
)

def run_import():
    """Executa o comando de importação de dados e recálculo de classificação."""
    logging.info("Iniciando atualização de dados do Football-Data.co.uk...")
    
    try:
        # 1. Importar dados (CSV)
        # min_year=2024 garante que pegamos a temporada atual e anterior se necessário
        # Ajuste o min_year conforme sua necessidade de histórico
        cmd_import = ["python", "manage.py", "import_football_data", "--division", "ALL", "--min_year", "2024"]
        subprocess.run(cmd_import, check=True)
        logging.info("Importação de CSV concluída com sucesso.")

        # 2. Recalcular tabelas (Standings)
        # É crucial rodar isso após importar jogos novos para atualizar a classificação
        cmd_standings = ["python", "manage.py", "recalculate_standings", "--league_name", "ALL"]
        subprocess.run(cmd_standings, check=True)
        logging.info("Tabelas recalculadas com sucesso.")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao executar comando: {e}")
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")

def main():
    logging.info("Iniciando monitor de atualizações (CSV)...")
    
    # Executa uma vez imediatamente ao iniciar
    run_import()

    # Agenda para rodar a cada 1 hora
    # O football-data.co.uk não é live score, então 1h é suficiente
    schedule.every(1).hours.do(run_import)
    
    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # Instalar schedule se não existir: pip install schedule
    try:
        import schedule
    except ImportError:
        print("Instalando biblioteca 'schedule' necessária...")
        subprocess.check_call(["pip", "install", "schedule"])
        import schedule
        
    main()
