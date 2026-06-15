from django.core.management.base import BaseCommand
from matches.services.live_lay_detector import LiveLayDetector

class Command(BaseCommand):
    help = 'Executa o Live Lay Detector para buscar oportunidades de Lay e enviar alertas via Telegram.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando Live Lay Detector..."))
        detector = LiveLayDetector()
        detector.process_live_matches()
        self.stdout.write(self.style.SUCCESS("Concluído."))
