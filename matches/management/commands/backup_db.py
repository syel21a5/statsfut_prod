import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Cria um backup rápido do banco de dados em formato JSON"

    def handle(self, *args, **options):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_statsfut_{timestamp}.json"
        
        self.stdout.write(f"Iniciando backup em {filename}...")
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                call_command("dumpdata", "--exclude", "auth.permission", "--exclude", "contenttypes", stdout=f)
            
            fullname = os.path.abspath(filename)
            self.stdout.write(self.style.SUCCESS(f"✅ Backup concluído com sucesso!"))
            self.stdout.write(self.style.SUCCESS(f"📍 Arquivo salvo em: {fullname}"))
            self.stdout.write(self.style.WARNING(f"📌 Dica: Baixe este arquivo via SFTP/FTP para seu computador."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro ao criar backup: {e}"))
