# SEO intro for Copa do Brasil (brazil/copa-do-brasil) — same flow as Missão 14 batches (inline texts: *.json is gitignored, so no file dependency)
from django.db import migrations
from django.utils.text import slugify

COPA_TEXTS = {
    'en': "The Copa do Brasil is Brazil's national knockout cup, where clubs from every division — from the Série A giants to the small state champions — fight for one of the most coveted trophies in South American football. Played in two-legged ties across several rounds, the competition is famous for its giant-killings, packed stadiums and do-or-die drama, with the champion earning a direct spot in the Copa Libertadores. Our Copa do Brasil statistics page brings you the full league table and fixtures, team form, goals trends, over/under percentages, home and away performance and complete head-to-head records for every round — everything you need for data-driven predictions and betting insights.",
    'pt': "A Copa do Brasil é a copa nacional de futebol do Brasil, onde clubes de todas as divisões — dos gigantes da Série A aos pequenos campeões estaduais — disputam um dos troféus mais cobiçados do futebol sul-americano. Disputada em jogos de ida e volta em várias fases, a competição é famosa pelas zebras, pelos estádios lotados e pela emoção do mata-mata, com o campeão garantindo vaga direta na Copa Libertadores. Nossa página de estatísticas da Copa do Brasil traz a tabela completa e os jogos, a forma dos times, as tendências de gols, os percentuais de mais/menos, o desempenho em casa e fora e o histórico completo de confrontos diretos em todas as fases — tudo o que você precisa para palpites e análises baseadas em dados.",
    'es': "La Copa do Brasil es la copa nacional de Brasil, donde clubes de todas las divisiones — desde los gigantes de la Série A hasta los pequeños campeones estaduales — pelean por uno de los trofeos más codiciados del fútbol sudamericano. Disputada en llaves de ida y vuelta a lo largo de varias fases, la competición es famosa por sus campanadas, los estadios llenos y la emoción a todo o nada, y el campeón asegura un puesto directo en la Copa Libertadores. Nuestra página de estadísticas de la Copa do Brasil incluye la tabla completa y los partidos, la forma de los equipos, las tendencias de goles, los porcentajes de más/menos, el rendimiento local y visitante y el historial completo de enfrentamientos directos en todas las fases: todo lo que necesitas para pronósticos y análisis basados en datos.",
    'de': "Die Copa do Brasil ist der brasilianische Nationalpokal, in dem Vereine aus allen Spielklassen — von den Giganten der Série A bis zu den kleinen Staatsmeistern — um eine der begehrtesten Trophäen des südamerikanischen Fußballs kämpfen. Gespielt wird in Hin- und Rückspielen über mehrere Runden; die Konkurrenz ist berühmt für ihre Sensationen, volle Stadien und die Dramatik des K.o.-Modus, und der Sieger qualifiziert sich direkt für die Copa Libertadores. Unsere Copa-do-Brasil-Statistikseite bietet die komplette Tabelle und die Spiele, Formkurven, Torentrends, Über/Unter-Quoten, Heim- und Auswärtsleistung sowie vollständige Direktvergleiche für jede Runde — alles für fundierte Tipps und datenbasierte Analysen.",
}

def load_seo_texts(apps, schema_editor):
    League = apps.get_model('matches', 'League')

    found = None
    for league in League.objects.all():
        if slugify(league.country) == 'brasil' and slugify(league.name) == 'copa-do-brasil':
            found = league
            break

    if found:
        found.intro_en = COPA_TEXTS['en']
        found.intro_pt = COPA_TEXTS['pt']
        found.intro_es = COPA_TEXTS['es']
        found.intro_de = COPA_TEXTS['de']
        found.save()
        print(f"[SEO] Liga atualizada: {found.country} / {found.name}")
    else:
        print("[!] Copa do Brasil nao encontrada no banco")

class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0046_add_big_chances'),
    ]

    operations = [
        migrations.RunPython(load_seo_texts, reverse_code=migrations.RunPython.noop),
    ]
