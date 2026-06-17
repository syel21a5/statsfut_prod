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
        
        # O nível de segurança exigido pela matemática (ex: 96% de chance de NÃO acontecer o placar)
        self.MIN_PROBABILITY_LAY = 96.0

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
            
            # Se ainda está 0-0, não há pânico no mercado
            if home_score == 0 and away_score == 0:
                return

            elapsed = match.elapsed_time or 0
            if match.status == 'HT':
                elapsed = 45
            
            # Filtro da Janela de Liquidez
            if elapsed < self.MIN_MINUTE or elapsed > self.MAX_MINUTE:
                return
                
            analyzer = MatchAnalyzer(match)
            stats = analyzer.generate_full_report()
            
            if not stats or 'poisson' not in stats:
                return
                
            cs_probs = stats['poisson'].get('correct_score', {})
            
            # Vamos encontrar o "Lay Seguro" ideal baseado na vantagem atual
            # Se o Time de Casa está ganhando, procuramos uma goleada absurda do Visitante (e vice-versa)
            best_lay_score = None
            best_prob = 0.0
            
            # Nós varremos todos os placares até 4 gols
            for h in range(5):
                for a in range(5):
                    # Não vamos mandar lay em placares que já aconteceram ou foram superados
                    if h < home_score or a < away_score:
                        continue
                        
                    score_str = f"{h}-{a}"
                    prob_to_happen = cs_probs.get(score_str, 0)
                    prob_to_fail = 100 - prob_to_happen
                    
                    # Se o placar exige uma virada colossal ou muitos gols, a chance de falhar é gigante
                    # Filtro de Cartão Vermelho (Regra 2)
                    red_cards_home = match.home_red or 0
                    red_cards_away = match.away_red or 0
                    
                    # Ajuste de probabilidade dinâmico baseado no cartão vermelho
                    # Se eu vou fazer Lay numa virada do Visitante, e o Visitante tem vermelho, fica ainda mais seguro
                    if a > away_score and red_cards_away > 0:
                        prob_to_fail += 2.0  # Fica ainda mais seguro
                    if h > home_score and red_cards_home > 0:
                        prob_to_fail += 2.0
                        
                    prob_to_fail = min(99.9, prob_to_fail)
                    
                    if prob_to_fail >= self.MIN_PROBABILITY_LAY:
                        # Precisamos garantir que esse placar seja o "próximo passo" ilógico do mercado
                        # Exemplo: Casa fez 1-0. Queremos fazer Lay no Casa 0-3 (Visitante virando).
                        # Vamos focar em vitórias esticadas do time que está perdendo ou do time que fez o gol 
                        # mas que o placar exija muitos gols adicionais
                        total_goals_needed = (h - home_score) + (a - away_score)
                        
                        if total_goals_needed >= 2:
                            if prob_to_fail > best_prob:
                                best_prob = prob_to_fail
                                best_lay_score = score_str

            if best_lay_score:
                self.send_telegram_alert(match, home_score, away_score, elapsed, best_lay_score, best_prob)

        except Exception as e:
            logger.error(f"Erro ao analisar jogo para Live Lay {match.id}: {str(e)}")

    def send_telegram_alert(self, match, h_score, a_score, elapsed, lay_score, prob):
        """Envia o alerta para o Telegram montando a mensagem visual."""
        
        # Para evitar spam de dezenas de mensagens para o mesmo jogo, deveríamos
        # guardar no banco ou no cache que esse alerta já foi enviado.
        # Por simplicidade, usamos cache.
        from django.core.cache import cache
        
        cache_key = f"live_lay_alert_{match.id}_{h_score}_{a_score}_{lay_score}"
        if cache.get(cache_key):
            return  # Já alertamos esse exato cenário hoje
            
        cache.set(cache_key, True, 60*60*4) # Salva por 4 horas para não repetir
        
        home_name = match.home_team.name
        away_name = match.away_team.name
        league = match.league.name
        
        msg = (
            f"🚨 <b>OPORTUNIDADE LIVE LAY (EXCHANGE)</b> 🚨\n\n"
            f"🏆 {league}\n"
            f"⚽ <b>{home_name} {h_score} x {a_score} {away_name}</b>\n"
            f"⏱️ <i>{elapsed}' minutos</i>\n\n"
            f"📉 <b>Alvo para Apostar CONTRA (Lay):</b> Placar <b>{lay_score}</b>\n"
            f"🛡️ <b>Chance de Sucesso:</b> {prob:.1f}%\n\n"
            f"💡 <i>Dica: O mercado se desesperou com o gol. A Odd desse Lay despencou, mas a matemática diz que é um placar quase impossível. Aproveite a liquidez!</i>"
        )
        
        logger.info(f"Disparando Alerta Telegram para {home_name} x {away_name} - Lay {lay_score}")
        TelegramBotService.send_message(msg)
