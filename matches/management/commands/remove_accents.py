from django.core.management.base import BaseCommand
import unicodedata
from matches.models import Team

class Command(BaseCommand):
    help = 'Remove acentos de todos os times do banco de dados (Produção)'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando remoção de acentos dos times...")
        
        teams = Team.objects.all()
        count = 0
        
        replacements = {
            'ø': 'o', 'Ø': 'O',
            'æ': 'ae', 'Æ': 'Ae',
            'ð': 'd', 'Ð': 'D',
            'þ': 'th', 'Þ': 'Th',
            'ß': 'ss'
        }
        
        for team in teams:
            old_name = team.name
            clean_name = old_name
            
            for char, replacement in replacements.items():
                clean_name = clean_name.replace(char, replacement)
                
            nfkd_form = unicodedata.normalize('NFKD', clean_name)
            new_name = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
            
            if old_name != new_name:
                team.name = new_name
                team.save()
                count += 1
                self.stdout.write(f"  Atualizado: {old_name} -> {new_name}")
                
        self.stdout.write(self.style.SUCCESS(f"\nFinalizado! {count} times foram atualizados."))
