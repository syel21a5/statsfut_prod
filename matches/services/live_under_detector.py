import math
import logging
from matches.models import Match
from matches.services.advanced_stats import MatchAnalyzer
from matches.services.telegram_bot import TelegramBotService

logger = logging.getLogger(__name__)


def poisson_prob(lam, k):
    """P(X=k) para distribuição de Poisson."""
    if lam <= 0:
        lam = 0.01
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)


class LiveUnderDetector:
    """
    Robô "Favorito Preguiçoso" — Detecta oportunidades de Under ao vivo.
    
    A tese: Quando o Super Favorito abre uma vantagem cedo (2-0 ou 3-0 no 1º tempo),
    ele tende a administrar o jogo e parar de atacar. O mercado, assustado pela
    velocidade dos gols, abre linhas de Over altíssimas (esperando goleada), mas
    a realidade é que o jogo esfria. Nós surfamos nesse Under.
    """

    def __init__(self):
        # Janela de Tempo: Apenas 1º tempo (entre 15' e 45')
        # Se o favorito já fez 2-0 antes dos 15 min, o mercado nem teve tempo de reagir.
        # Depois dos 45 min, o intervalo "reseta" a mentalidade dos jogadores.
        self.MIN_MINUTE = 15
        self.MAX_MINUTE = 45

        # Diferença mínima de gols para considerar "vantagem construída"
        self.MIN_GOAL_DIFF = 2

        # Probabilidade mínima pré-jogo de vitória do favorito (65%)
        self.MIN_FAVORITE_PROB = 55

        # Probabilidade mínima do Under para enviar a Tip
        self.MIN_UNDER_PROB = 70.0

    def process_live_matches(self):
        """Busca jogos ao vivo e analisa oportunidades de Under."""
        logger.info("🛡️ Verificando oportunidades Under (Favorito Preguiçoso)...")

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
            goal_diff = abs(home_score - away_score)

            # Filtro 1: Precisa ter pelo menos 2 gols de vantagem
            if goal_diff < self.MIN_GOAL_DIFF:
                return

            # Filtro 2: Janela de tempo (1º tempo, entre 15' e 45')
            elapsed = match.elapsed_time or 0
            if match.status == 'HT':
                elapsed = 45
            if elapsed < self.MIN_MINUTE or elapsed > self.MAX_MINUTE:
                return

            # Filtro 3: Verificar se quem está ganhando é o Super Favorito
            analyzer = MatchAnalyzer(match)
            probs = analyzer.get_match_odds_probs()

            if not probs:
                return

            # Identifica quem é o favorito e se ele está ganhando
            home_prob = probs.get('home_win', 0)
            away_prob = probs.get('away_win', 0)

            home_is_favorite = home_prob >= self.MIN_FAVORITE_PROB
            away_is_favorite = away_prob >= self.MIN_FAVORITE_PROB

            favorite_winning = False
            if home_is_favorite and home_score > away_score:
                favorite_winning = True
                fav_name = match.home_team.name
                fav_prob = home_prob
            elif away_is_favorite and away_score > home_score:
                favorite_winning = True
                fav_name = match.away_team.name
                fav_prob = away_prob

            if not favorite_winning:
                return

            # Filtro 4: Cartão Vermelho no time que está perdendo NÃO é bom
            # Se a zebra tomou vermelho, o favorito vai massacrar = mais gols = Under perde
            red_cards_home = match.home_red_cards or 0
            red_cards_away = match.away_red_cards or 0

            if home_score > away_score and red_cards_away > 0:
                return  # Zebra com 1 a menos = favorito vai golear
            if away_score > home_score and red_cards_home > 0:
                return

            # Calcular probabilidades de Under usando Poisson com tempo restante
            general = analyzer.get_general_form()
            xg_home = ((general['home']['avg_gf'] + general['away']['avg_ga']) / 2) * 1.10
            xg_away = ((general['away']['avg_gf'] + general['home']['avg_ga']) / 2) * 0.90

            # Ajustar xG pelo tempo restante (regra de 3)
            remaining_fraction = (90 - elapsed) / 90
            xg_remaining_home = xg_home * remaining_fraction
            xg_remaining_away = xg_away * remaining_fraction

            # Fator "Preguiça": Se o favorito já está ganhando de 2+, reduzimos o xG dele em 25%
            if home_score > away_score:
                xg_remaining_home *= 0.75  # Favorito tira o pé
            else:
                xg_remaining_away *= 0.75

            xg_remaining_total = xg_remaining_home + xg_remaining_away

            # Calcular probabilidades de Under para diferentes linhas
            under_lines = {}
            for line in [3.5, 4.5, 5.5]:
                goals_needed_for_over = line - total_goals
                if goals_needed_for_over <= 0:
                    # Já passou dessa linha, Under já perdeu
                    under_lines[line] = 0.0
                    continue

                # P(Under) = P(gols restantes < goals_needed_for_over)
                prob_under = 0.0
                for k in range(int(goals_needed_for_over)):
                    prob_under += poisson_prob(xg_remaining_total, k)

                under_lines[line] = round(prob_under * 100, 1)

            # Filtrar apenas as linhas que passam no nosso critério mínimo
            valid_tips = {
                line: prob for line, prob in under_lines.items()
                if prob >= self.MIN_UNDER_PROB
            }

            if valid_tips:
                self.send_telegram_alert(
                    match, home_score, away_score, elapsed,
                    fav_name, fav_prob, valid_tips
                )

        except Exception as e:
            logger.error(f"Erro ao analisar Under para jogo {match.id}: {str(e)}")

    def send_telegram_alert(self, match, h_score, a_score, elapsed, fav_name, fav_prob, tips):
        """Envia o alerta de Under para o Telegram."""
        from django.core.cache import cache

        # Anti-spam: Uma mensagem por jogo por placar
        cache_key = f"live_under_alert_{match.id}_{h_score}_{a_score}"
        if cache.get(cache_key):
            return
        cache.set(cache_key, True, 60 * 60 * 4)

        home_name = match.home_team.name
        away_name = match.away_team.name
        league = match.league.name

        # Montar as linhas de recomendação
        tips_lines = ""
        best_line = None
        best_ratio = 0

        for line, prob in sorted(tips.items()):
            emoji = "🟢" if prob >= 85 else "🟡"
            tips_lines += f"{emoji} Under {line} → {prob}% de acerto\n"

            # Calcular melhor custo-benefício (prob vs risco)
            # Under 4.5 com 78% é melhor que Under 5.5 com 93%
            # porque a odd do 4.5 paga mais
            ratio = prob * (line - (h_score + a_score))
            if ratio > best_ratio:
                best_ratio = ratio
                best_line = line

        suggestion = ""
        if best_line:
            suggestion = f"\n💡 <i>Sugestão: Under {best_line} oferece a melhor relação risco/retorno.</i>"

        msg = (
            f"🛡️ <b>UNDER ALERT - Favorito Preguiçoso</b> 🛡️\n\n"
            f"🏆 {league}\n"
            f"⚽ <b>{home_name} {h_score} x {a_score} {away_name}</b>\n"
            f"⏱️ <i>{elapsed}' minutos (1º Tempo)</i>\n"
            f"👑 Favorito: <b>{fav_name}</b> ({fav_prob}% pré-jogo)\n\n"
            f"📊 <b>Recomendações:</b>\n"
            f"{tips_lines}"
            f"{suggestion}\n\n"
            f"💤 <i>O favorito construiu vantagem cedo e tende a administrar o jogo. "
            f"O mercado espera goleada, mas a matemática diz que o jogo vai esfriar.</i>"
        )

        logger.info(f"Disparando Under Alert para {home_name} x {away_name}")
        TelegramBotService.send_message(msg)
