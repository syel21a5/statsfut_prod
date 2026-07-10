import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "statsfut.settings")
django.setup()

from matches.models import League, Team, Match

def run():
    # 1. Pega a liga Tcheca (ID 25)
    liga = League.objects.get(id=25)

    print(f"Limpando a liga: {liga.name} ({liga.country})")

    # 2. Deleta os jogos vinculados a ela (os jogos da Armênia que entraram agora e outros lixos)
    jogos_apagados, _ = Match.objects.filter(league=liga).delete()
    print(f"Apagados {jogos_apagados} jogos.")

    # 3. Deleta os times da Armênia vinculados a ela
    times_apagados, _ = Team.objects.filter(league=liga).delete()
    print(f"Apagados {times_apagados} times.")

    # 4. Corrige o API ID no banco de dados para o correto da República Tcheca (345)
    liga.api_id = 345
    liga.save(update_fields=['api_id'])
    print(f"API ID corrigido para {liga.api_id} (Czech Liga)!")

if __name__ == '__main__':
    run()
