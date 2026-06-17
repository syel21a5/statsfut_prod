import logging
from matches.models import Match
from matches.services.advanced_stats import MatchAnalyzer
from matches.services.telegram_bot import TelegramBotService

logger = logging.getLogger(__name__)

class LiveUnderDetector:
    """
    Robô Under Dinâmico — Detecta oportunidades imediatamente após um gol rápido.
    Foco: Under 4.5 e Under 5.5 em jogos com baixíssima probabilidade matemática de over.
    """

    def __init__(self):
        # Janela de Tempo: Apenas 1º tempo, gol ocorrido antes dos 35 minutos
        self.MAX_MINUTE = 35

        # Probabilidade máxima do Over 4.5 para enviar a Tip (15%)
        # Se Over 4.5 <= 15%, significa que Under 4.5 >= 85% (Muito seguro)
        self.MAX_OVER_45_PROB = 15.0

    def process_live_matches(self):
        """Busca jogos ao vivo e analisa oportunidades de Under."""
        logger.info("🛡️ Verificando oportunidades Under (Gol Rápido)...")

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

            # Filtro 1: Exatamente 1 gol no jogo
            if total_goals != 1:
                return

            # Filtro 2: Janela de tempo (Gol Rápido, no 1º tempo)
            elapsed = match.elapsed_time or 0
            if match.status == 'HT':
                elapsed = 45

            if elapsed > self.MAX_MINUTE:
                return

            # Verifica cartões vermelhos (Se saiu gol e tem vermelho, o jogo pode descarrilar)
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

            # Filtro 3: Validação Matemática (Probabilidade de Over 4.5 <= 15%)
            if over_45_prob <= self.MAX_OVER_45_PROB:
                self.send_telegram_alert(
                    match, home_score, away_score, elapsed, over_45_prob
                )

        except Exception as e:
            logger.error(f"Erro ao analisar Under para jogo {match.id}: {str(e)}")

    def send_telegram_alert(self, match, h_score, a_score, elapsed, over_45_prob):
        """Envia o alerta imediato de Under para o Telegram."""
        from django.core.cache import cache

        # Anti-spam: Uma mensagem por jogo
        cache_key = f"live_under_alert_{match.id}_goal_1"
        if cache.get(cache_key):
            return
        cache.set(cache_key, True, 60 * 60 * 4)

        home_name = match.home_team.name
        away_name = match.away_team.name
        league = match.league.name
        
        under_45_prob = 100 - over_45_prob

        msg = (
            f"🛡️ <b>ALERTA UNDER - GOL RÁPIDO</b> 🛡️\n\n"
            f"🏆 {league}\n"
            f"⚽ <b>{home_name} {h_score} x {a_score} {away_name}</b>\n"
            f"⏱️ <i>{elapsed}' minutos (1º Tempo)</i>\n\n"
            f"📊 <b>A Matemática a Nosso Favor:</b>\n"
            f"Mesmo com esse gol cedo, o modelo aponta que o jogo tem APENAS <b>{over_45_prob}%</b> de chance de bater Over 4.5.\n\n"
            f"💡 <b>Recomendação:</b>\n"
            f"Fique de olho nas linhas seguras:\n"
            f"🟢 <b>Under 4.5</b> (Aproximadamente {under_45_prob}% de Win Rate)\n"
            f"🟢 <b>Under 5.5</b> (Extremamente Seguro)\n\n"
            f"<i>O mercado se assustou com esse gol rápido. Se você confia na estatística pré-jogo, as odds para Under 4.5 acabaram de ganhar muito valor!</i>"
        )

        logger.info(f"Disparando Under Alert Dinâmico para {home_name} x {away_name} (Over 4.5 = {over_45_prob}%)")
        TelegramBotService.send_message(msg)
