import logging
from matches.models import Match
from matches.services.advanced_stats import MatchAnalyzer
from matches.services.telegram_bot import TelegramBotService

logger = logging.getLogger(__name__)

class LiveUnderDetector:
    """
    Robô Under Dinâmico — Múltiplos Módulos de Distorção de Mercado.
    Foco: Encontrar jogos com forte matemática Under (<= 15% Over 4.5)
    e surfar o pânico do mercado quando gols saem muito rápido.
    """

    def __init__(self):
        # A Janela Mestra: Tudo tem que acontecer no 1º tempo
        self.MAX_MINUTE = 40

        # A Regra de Ouro Inquebrável: Over 4.5 deve ser <= 15%
        self.MAX_OVER_45_PROB = 15.0

    def process_live_matches(self):
        """Busca jogos ao vivo e analisa oportunidades de Under."""
        logger.info("🛡️ Verificando oportunidades Under Dinâmico...")

        live_matches = Match.objects.filter(
            status__in=['1H', '2H', 'HT', 'In Progress', 'Live']
        ).select_related('home_team', 'away_team', 'league')

        for match in live_matches:
            self.analyze_match(match)

    def analyze_match(self, match):
        try:
            home_score = match.home_score or 0
            away_score = match.away_score or 0
            total_goals = home_score + away_score

            # Filtro 1: O jogo precisa ter entre 1 e 3 gols
            if total_goals not in [1, 2, 3]:
                return

            # Filtro 2: Janela de tempo (Tem que ser rápido, até uns 40 min)
            elapsed = match.elapsed_time or 0
            if match.status == 'HT':
                elapsed = 45

            if elapsed > self.MAX_MINUTE:
                return

            # Verifica cartões vermelhos (Vermelho desconfigura o modelo Under)
            red_cards_home = match.home_red_cards or 0
            red_cards_away = match.away_red_cards or 0
            if red_cards_home > 0 or red_cards_away > 0:
                return

            # Analisa as estatísticas
            analyzer = MatchAnalyzer(match)
            stats = analyzer.generate_full_report()

            if not stats or 'goals' not in stats:
                return

            over_45_prob = stats['goals'].get('over_45', 100)

            # Filtro 3 (REGRA DE OURO): Validação Matemática
            if over_45_prob <= self.MAX_OVER_45_PROB:
                self.send_telegram_alert(
                    match, home_score, away_score, elapsed, over_45_prob, total_goals
                )

        except Exception as e:
            logger.error(f"Erro ao analisar Under para jogo {match.id}: {str(e)}")

    def send_telegram_alert(self, match, h_score, a_score, elapsed, over_45_prob, total_goals):
        from django.core.cache import cache

        # Anti-spam: Uma mensagem por jogo baseado no número de gols
        # Assim ele avisa se sair o 1º gol, e se sair o 2º ou 3º muito rápido, ele avisa de novo!
        cache_key = f"live_under_alert_{match.id}_goals_{total_goals}"
        if cache.get(cache_key):
            return
        cache.set(cache_key, True, 60 * 60 * 4)

        home_name = match.home_team.name
        away_name = match.away_team.name
        league = match.league.name
        under_45_prob = 100 - over_45_prob

        # Módulos de Mensagem Dinâmica
        if total_goals == 1:
            titulo = "GOL RÁPIDO (Susto Inicial)"
            obs = "O mercado se assustou com esse primeiro gol. As odds para Under 4.5 acabaram de ganhar muito valor!"
            linhas = f"🟢 <b>Under 4.5</b>\n🟢 <b>Under 5.5</b> (Muito Seguro)"
        elif total_goals == 2:
            titulo = "PÂNICO DO MERCADO (2 Gols)"
            obs = "Dois gols tão cedo num jogo de tendência Under! O mercado entrou em colapso projetando uma chuva de gols. Abrace as linhas altas."
            linhas = f"🟢 <b>Under 4.5</b> (Para ótimo lucro)\n🟢 <b>Under 5.5</b> (Para segurança máxima)"
        elif total_goals == 3:
            titulo = "A FALSA GOLEADA (3 Gols)"
            obs = "O mercado tem certeza que vai terminar 6x0. Mas a matemática diz que o jogo morre agora e as equipes vão se fechar. As odds do Under estão esmagadoras!"
            linhas = f"🟢 <b>Under 5.5</b>\n🟢 <b>Under 6.5</b> (Risco quase zero)"

        msg = (
            f"🛡️ <b>ALERTA UNDER: {titulo}</b> 🛡️\n\n"
            f"🏆 {league}\n"
            f"⚽ <b>{home_name} {h_score} x {a_score} {away_name}</b>\n"
            f"⏱️ <i>{elapsed}' minutos (1º Tempo)</i>\n\n"
            f"📊 <b>A Regra de Ouro (Matemática):</b>\n"
            f"A chance deste jogo bater Over 4.5 Gols é de apenas <b>{over_45_prob}%</b>.\n"
            f"<i>Isso significa {under_45_prob}% de segurança.</i>\n\n"
            f"💡 <b>Recomendação:</b>\n"
            f"Fique de olho nas linhas com odd esticada:\n"
            f"{linhas}\n\n"
            f"<i>{obs}</i>"
        )

        logger.info(f"Disparando Under Alert Dinâmico para {home_name} x {away_name} ({total_goals} gols)")
        TelegramBotService.send_message(msg)
