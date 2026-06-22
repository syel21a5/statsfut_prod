import logging
from matches.models import Match
from matches.services.advanced_stats import MatchAnalyzer
from matches.services.telegram_bot import TelegramBotService

logger = logging.getLogger(__name__)

class LiveUnderDetector:
    """
    Robô Under Dinâmico — Radar Completo de Oportunidades no 1º Tempo.
    Foco: Encontrar jogos com forte matemática Under (<= 15% Over 4.5).
    Fases:
    1. Radar Inicial (0x0 nos primeiros 10min)
    2. Surfar o Pânico do mercado se saírem gols (1, 2, 3...) no 1º tempo.
    """

    def __init__(self):
        # A Janela Mestra: Tudo tem que acontecer no 1º tempo (até 45' + acréscimos)
        self.MAX_MINUTE = 45

        # A Regra de Ouro Inquebrável: Over 4.5 deve ser <= 15%
        self.MAX_OVER_45_PROB = 15.0

    def process_live_matches(self):
        """Busca jogos ao vivo e analisa oportunidades de Under."""
        logger.info("🛡️ Verificando oportunidades Under Dinâmico (Radar HT)...")

        live_matches = Match.objects.filter(
            status__in=['1H', 'HT', 'In Progress', 'Live']
        ).select_related('home_team', 'away_team', 'league')

        for match in live_matches:
            self.analyze_match(match)

    def analyze_match(self, match):
        try:
            # Garante que só olha para o Primeiro Tempo
            if match.status in ['2H', 'FT', 'Finished', 'Match Finished']:
                return

            home_score = match.home_score or 0
            away_score = match.away_score or 0
            total_goals = home_score + away_score

            # Filtro de tempo
            elapsed = match.elapsed_time or 0
            if match.status == 'HT':
                elapsed = 45

            if elapsed > self.MAX_MINUTE and match.status != 'HT':
                return

            # Para o RADAR de 0x0, só queremos avisar bem no comecinho (ex: até 15 min)
            if total_goals == 0 and elapsed > 15:
                return

            # A remoção do filtro de cartão vermelho foi solicitada pelo usuário.
            # O usuário validará os cartões vermelhos manualmente na casa de apostas.

            # Analisa as estatísticas
            analyzer = MatchAnalyzer(match)
            stats = analyzer.generate_full_report()

            if not stats or 'goals' not in stats:
                return

            over_45_prob = stats['goals'].get('over_45', 100)
            over_35_prob = stats['goals'].get('over_35', 100)

            # Filtro Mestre: Validação Matemática
            if over_45_prob <= self.MAX_OVER_45_PROB and over_35_prob <= 25.0:
                self.send_telegram_alert(
                    match, home_score, away_score, elapsed, over_45_prob, total_goals
                )

        except Exception as e:
            logger.error(f"Erro ao analisar Under para jogo {match.id}: {str(e)}")

    def send_telegram_alert(self, match, h_score, a_score, elapsed, over_45_prob, total_goals):
        from matches.models import ScannerTip

        # Anti-spam definitivo via Banco de Dados
        market_key = f"TLGRM_UNDER_{total_goals}_GOLS"
        tip, created = ScannerTip.objects.get_or_create(
            match=match,
            market=market_key,
            defaults={
                'prediction_text': f"Telegram Under Alert ({total_goals} Gols)",
                'probability': over_45_prob,
                'status': 'PENDING'
            }
        )
        
        # Se não foi criado agora, é porque já tínhamos salvo no banco que a mensagem foi enviada
        if not created:
            return

        home_name = match.home_team.name
        away_name = match.away_team.name
        league = match.league.name
        under_45_prob = 100 - over_45_prob

        # Módulos de Mensagem Dinâmica
        if total_goals == 0:
            titulo = "RADAR (Jogo Promissor)"
            obs = ("Partida excelente para a estratégia Under! Favorite na corretora e aguarde.\n"
                   "⚠️ <b>NÃO entre agora:</b> Aguarde o primeiro gol em 0x0 para fazer a entrada + proteções juntas.")
            linhas = f"🟢 <b>Favoritar o Jogo</b> (Aguardar 1º gol)"
        elif total_goals == 1:
            if elapsed <= 15:
                titulo = "GOL CEDO (Blindagem Total ou Under 4.5)"
                obs = (f"Gol muito cedo aos {elapsed}'min! Risco de goleada ativa.\n"
                       "👉 <b>Como agir profissionalmente (Stake R$ 50):</b>\n"
                       "1. <b>Linha Conservadora:</b> Entre no <b>Under 4.5</b> (R$ 50) e proteja apenas com R$ 2,50 no AOV Casa e R$ 1,00 no AOV Visitante.\n"
                       "2. <b>Linha Blindagem Total:</b> Entre no <b>Under 3.5</b> (R$ 50) e coloque seguros de R$ 1,00 a R$ 3,50 no AOV Casa/Vis e nos placares (2-2, 3-1, 1-3, 3-2, 2-3) para cobrir 100% dos cenários.")
                linhas = f"🟢 <b>Under 4.5</b> (Seguro) ou <b>Under 3.5</b> (Com 7 Proteções)"
            elif elapsed <= 30:
                titulo = "GOL INTERMEDIÁRIO (Under 3.5 Protegido)"
                obs = (f"Gol aos {elapsed}'min! A chance de goleada caiu. O inimigo é o placar de 4 gols.\n"
                       "👉 <b>Como agir profissionalmente (Stake R$ 50):</b>\n"
                       "Entre no <b>Under 3.5</b> (R$ 50) e proteja apenas os placares de 4 gols: R$ 2,00 no 2-2, R$ 2,00 no 3-1 e R$ 1,00 no 1-3. (Economiza R$ 10 em seguros).")
                linhas = f"🟢 <b>Under 3.5</b> (Com proteção apenas de 4 gols)"
            else:
                titulo = "GOL NO FIM DO HT (Under 3.5 ou Under 2.5)"
                obs = (f"Gol tardio aos {elapsed}'min! Perto do intervalo.\n"
                       "👉 <b>Como agir profissionalmente (Stake R$ 50):</b>\n"
                       "1. <b>Seguro:</b> Entre no <b>Under 3.5</b> seco (R$ 50) sem proteções.\n"
                       "2. <b>Agressivo:</b> Entre no <b>Under 2.5</b> (R$ 50) e coloque apenas R$ 2,00 no 2-1 e R$ 1,00 no 1-2 de proteção.")
                linhas = f"🟢 <b>Under 3.5</b> (Sem seguro) ou <b>Under 2.5</b> (Protegido no 2-1/1-2)"
        elif total_goals == 2:
            titulo = "PÂNICO DO MERCADO (2 Gols)"
            obs = "Dois gols tão cedo num jogo de tendência Under! O mercado entrou em colapso projetando uma chuva de gols. Abrace as linhas altas."
            linhas = f"🟢 <b>Under 4.5</b> (Para ótimo lucro)\n🟢 <b>Under 5.5</b> (Para segurança máxima)"
        elif total_goals >= 3:
            titulo = f"A FALSA GOLEADA ({total_goals} Gols)"
            obs = "O mercado tem certeza que vai terminar 6x0. Mas a matemática diz que o jogo morre agora e as equipes vão se fechar. As odds do Under estão esmagadoras!"
            linhas = f"🟢 <b>Under {total_goals + 1}.5</b>\n🟢 <b>Under {total_goals + 2}.5</b> (Risco quase zero)"

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
