import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, League

def check_prod_data():
    print("--- Verificação de Dados em Produção ---")
    
    # Austrália (ID 21)
    try:
        l_aus = League.objects.get(id=21)
        m_aus = Match.objects.filter(league=l_aus).count()
        print(f"Austrália (ID 21): {m_aus} jogos")
    except:
        print("Austrália (ID 21) não encontrada ou erro.")

    # Áustria (ID 44)
    try:
        l_aut = League.objects.get(id=44)
        m_aut = Match.objects.filter(league=l_aut).count()
        print(f"Áustria (ID 44): {m_aut} jogos")
    except:
        print("Áustria (ID 44) não encontrada ou erro.")

if __name__ == '__main__':
    check_prod_data()
