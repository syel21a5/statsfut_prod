from matches.models import Match
from matches.services.advanced_stats import MatchAnalyzer
from matches.services.telegram_bot import TelegramBotService
import logging

logger = logging.getLogger(__name__)

class LiveLayDetector:
    def __init__(self):
        # A "Janela de Liquidez" (Regra 3)
        # Onde o mercado ainda acredita em gols, mas a matemática sabe que é improvável
        self.MIN_MINUTE = 15
        self.MAX_MINUTE = 65
        
        # O nível de segurança exigido pela matemática (ex: 90% de chance de NÃO acontecer o placar)
        self.MIN_PROBABILITY_LAY = 90.0

    def process_live_matches(self):
        """Busca jogos ao vivo e envia alertas se oportunidades forem encontradas."""
        logger.info("Verificando oportunidades Live Lay...")
        
        # Filtra jogos que estão em andamento (1º Tempo, 2º Tempo, Intervalo)
        live_matches = Match.objects.filter(status__in=['1H', '2H', 'HT', 'In Progress', 'Live']).select_related('home_team', 'away_team')
        
        for match in live_matches:
            self.analyze_match(match)

    def analyze_match(self, match):
        try:
            home_score = match.home_score or 0
            away_score = match.away_score or 0
            
            # Fase 0: RADAR INICIAL (0-0, Primeiros 15 minutos)
            if home_score == 0 and away_score == 0 and elapsed <= 15:
                self._process_radar_phase(match, elapsed, stats)
                return
                
            # Fase 1: PÂNICO DO MERCADO (15 aos 65 minutos, jogo com gols)
            # Filtro da Janela de Liquidez
            if elapsed < self.MIN_MINUTE or elapsed > self.MAX_MINUTE:
                return
                
            if home_score == 0 and away_score == 0:
                return # Pânico só acontece com gol
                
            cs_probs = stats['poisson'].get('correct_score', {})
            best_lay_score = None
            best_prob = 0.0
            
            for h in range(5):
                for a in range(5):
                    if h < home_score or a < away_score:
                        continue
                        
                    score_str = f"{h}-{a}"
                    prob_to_happen = cs_probs.get(score_str, 0)
                    prob_to_fail = min(99.9, 100 - prob_to_happen)
                    
                    if prob_to_fail >= self.MIN_PROBABILITY_LAY:
                        total_goals_needed = (h - home_score) + (a - away_score)
                        
                        if total_goals_needed >= 2:
                            if prob_to_fail > best_prob:
                                best_prob = prob_to_fail
                                best_lay_score = score_str

            if best_lay_score:
                self.send_panic_alert(match, home_score, away_score, elapsed, best_lay_score, best_prob)

        except Exception as e:
            logger.error(f"Erro ao analisar jogo para Live Lay {match.id}: {str(e)}")

    def _process_radar_phase(self, match, elapsed, stats):
        from matches.models import ScannerTip
        
        market_key = f"TLGRM_LAY_RADAR"
        tip, created = ScannerTip.objects.get_or_create(
            match=match,
            market=market_key,
            defaults={
                'prediction_text': "Telegram Lay Radar",
                'probability': 0,
                'status': 'PENDING'
            }
        )
        if not created:
            return
            
        probs = MatchAnalyzer(match).get_match_odds_probs()
        if not probs:
            return
            
        home_win = probs.get('home_win', 33)
        away_win = probs.get('away_win', 33)
        
        # Determina quem é o favorito matematicamente
        if home_win >= away_win:
            fav_name = match.home_team.name
            fav_prob = home_win
        else:
            fav_name = match.away_team.name
            fav_prob = away_win

        cs_probs = stats['poisson'].get('correct_score', {})
        safe_lays = []
        
        for h in range(5):
            for a in range(5):
                prob_to_fail = min(99.9, 100 - cs_probs.get(f"{h}-{a}", 0))
                if prob_to_fail >= self.MIN_PROBABILITY_LAY:
                    safe_lays.append((f"{h}-{a}", prob_to_fail))
                    
        # Ordena para pegar os placares mais absurdos/impossíveis primeiro
        safe_lays.sort(key=lambda x: x[1], reverse=True)
        top_lays = safe_lays[:3] # Pega os 3 melhores
        
        if not top_lays:
            return
        
        linhas_str = "\n".join([f"🔴 <b>Lay {score}</b> ({prob:.1f}% Seguro)" for score, prob in top_lays])
        
        msg = (
            f"📡 <b>RADAR LIVE LAY (Início de Jogo)</b> 📡\n\n"
            f"🏆 {match.league.name}\n"
            f"⚽ <b>{match.home_team.name} 0 x 0 {match.away_team.name}</b>\n"
            f"⏱️ <i>{elapsed}' minutos</i>\n\n"
            f"👑 <b>Favorito Matemático:</b> {fav_name} ({fav_prob:.1f}%)\n\n"
            f"🛡️ <b>Top 3 Placares para Apostar CONTRA:</b>\n"
            f"{linhas_str}\n\n"
            f"💡 <i>Dica: O jogo começou agora. Esses são os placares que a matemática praticamente descarta. Deixe na mira da Exchange!</i>"
        )
        
        logger.info(f"Disparando RADAR Lay para {match.home_team.name} x {match.away_team.name}")
        TelegramBotService.send_message(msg)

    def send_panic_alert(self, match, h_score, a_score, elapsed, lay_score, prob):
        """Envia o alerta para o Telegram montando a mensagem visual."""
        
        from matches.models import ScannerTip
        
        market_key = f"TLGRM_LAY_PANIC_{h_score}_{a_score}_{lay_score}"
        tip, created = ScannerTip.objects.get_or_create(
            match=match,
            market=market_key,
            defaults={
                'prediction_text': f"Telegram Lay Panic ({lay_score})",
                'probability': prob,
                'status': 'PENDING'
            }
        )
        if not created:
            return  # Já alertamos esse exato cenário hoje
        
        home_name = match.home_team.name
        away_name = match.away_team.name
        league = match.league.name
        
        msg = (
            f"🚨 <b>OPORTUNIDADE LIVE LAY (Pânico no Mercado)</b> 🚨\n\n"
            f"🏆 {league}\n"
            f"⚽ <b>{home_name} {h_score} x {a_score} {away_name}</b>\n"
            f"⏱️ <i>{elapsed}' minutos</i>\n\n"
            f"📉 <b>Alvo para Apostar CONTRA (Lay):</b> Placar <b>{lay_score}</b>\n"
            f"🛡️ <b>Chance de Sucesso:</b> {prob:.1f}%\n\n"
            f"💡 <i>Dica: O mercado se desesperou com o gol. A Odd desse Lay despencou, mas a matemática diz que é um placar extremamente improvável. Aproveite a liquidez!</i>"
        )
        
        logger.info(f"Disparando Alerta Lay (Pânico) para {home_name} x {away_name} - Lay {lay_score}")
        TelegramBotService.send_message(msg)
