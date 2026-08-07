from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'DEPRECATED: Use scrape_soccerstats_brazil instead'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.ERROR('Este comando foi descontinuado. Por favor, use: python manage.py scrape_soccerstats_brazil'))
