import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.management import call_command

leagues_to_export = [
    ("Ligue 1", 2016), ("Ligue 1", 2017), ("Ligue 1", 2018), 
    ("Ligue 1", 2019), ("Ligue 1", 2020), ("Ligue 1", 2021), 
    ("Ligue 1", 2022), ("Ligue 1", 2023), ("Ligue 1", 2024), 
    ("Ligue 1", 2025)
]

for league, year in leagues_to_export:
    print(f"Exportando {league} {year}...")
    call_command('export_historical_csv', league=league, year=year)

# Mover os arquivos para a pasta correta
source_dir = "historical_data"
target_dir = os.path.join("historical_data", "France", "Ligue 1")

if not os.path.exists(target_dir):
    os.makedirs(target_dir)

for file in os.listdir(source_dir):
    if file.endswith("_backup.csv") and "Ligue 1" in file:
        os.rename(os.path.join(source_dir, file), os.path.join(target_dir, file))
        print(f"Movido: {file} -> {target_dir}")
