from django.core.management.base import BaseCommand
from matches.services.live_lay_detector import LiveLayDetector
from matches.services.live_under_detector import LiveUnderDetector

class Command(BaseCommand):
    help = 'Executa todos os Robôs de Telegram ao vivo (Lay + Under).'

    def handle(self, *args, **options):
        # Robô 1: Lay Correct Score (Apostar contra placares impossíveis)
        self.stdout.write(self.style.NOTICE("🎯 Robô 1: Live Lay Detector..."))
        try:
            lay_detector = LiveLayDetector()
            lay_detector.process_live_matches()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro no Lay Detector: {e}"))

        # Robô 2: Under "Favorito Preguiçoso" (Surfar no jogo que esfria)
        self.stdout.write(self.style.NOTICE("🛡️ Robô 2: Under Detector..."))
        try:
            under_detector = LiveUnderDetector()
            under_detector.process_live_matches()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro no Under Detector: {e}"))

        self.stdout.write(self.style.SUCCESS("✅ Todos os robôs concluídos."))

