from django.core.management.base import BaseCommand
from matches.services.live_over_detector import LiveOverDetector

class Command(BaseCommand):
    help = 'Robô Over 1.5 FT — Drip Staking (3 entradas fracionadas: 20, 27, 35 min).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("⚡ Robô Over 1.5: Drip Staking Detector..."))
        try:
            detector = LiveOverDetector()
            detector.process_live_matches()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro no Over Detector: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("✅ Robô Over 1.5 concluído."))