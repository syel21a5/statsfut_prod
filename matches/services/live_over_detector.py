import logging
from django.conf import settings
from matches.models import Match, ScannerTip
from matches.services.advanced_stats import MatchAnalyzer
from matches.services.telegram_bot import TelegramBotService

logger = logging.getLogger(__name__)

class LiveOverDetector:
    """
    Robô Over 1.5 FT — Drip Staking (Estratégia do Blog).
    Baseado no artigo: "Parte 3 - Over 1.5 FT (Live Trading Avançado)"
    
    Estratégia:
    1. Radar: jogos ao vivo com over_15 >= 66%
    2. 0-20': Proibido entrar (deixar odd engordar)
    3. 20' (0x0): 1ª entrada (1/3)
    4. 27' (0x0): 2ª entrada (1/3)
    5. 35' (0x0): 3ª entrada (1/3)
    6. Gol na fase de entrada (20-45'): LAY no Over 1.5 = Free Bet
    7. 0-0 no HT: Segurar, confiar no método
    """

    def __init__(self):
        # Régua: over_15 mínimo para considerar um jogo com tendência Over
        self.MIN_OVER_15_PROB = 66.0

        # Stake total sugerida (o usuário ajusta na prática)
        self.STAKE_TOTAL = 50.0
        self.STAKE_TERCO = round(self.STAKE_TOTAL / 3, 2)  # ~16.67

        # Janelas de entrada
        self.ENTRY_WINDOW = 2  # tolerância em minutos para o alerta

        # Chat DEDICADO do Over (separado do Under). Se não configurado,
        # o robô NÃO envia nada (nunca usa o chat do Under).
        self.OVER_CHAT_ID = getattr(settings, 'TELEGRAM_CHAT_ID_OVER', '') or ''

    def _send(self, msg):
        """Envia mensagem SOMENTE para o chat dedicado do Over.
        Se TELEGRAM_CHAT_ID_OVER não estiver configurado, NÃO envia
        (nunca cai no grupo do Under). Apenas registra no log."""
        if not self.OVER_CHAT_ID:
            logger.warning("TELEGRAM_CHAT_ID_OVER não configurado — alerta Over NÃO enviado (protegendo o grupo do Under).")
            return False
        return TelegramBotService.send_message(msg, chat_id=self.OVER_CHAT_ID)

    def process_live_matches(self):
        """Busca jogos ao vivo e analisa oportunidades de Over 1.5."""
        logger.info("⚡ Verificando oportunidades Over 1.5 (Drip Staking)...")

        live_matches = Match.objects.filter(
            status__in=['1H', '2H', 'HT', 'In Progress', 'Live']
        ).select_related('home_team', 'away_team', 'league')

        for match in live_matches:
            self.analyze_match(match)

    def analyze_match(self, match):
        try:
            elapsed = match.elapsed_time or 0
            home_score = match.home_score or 0
            away_score = match.away_score or 0
            total_goals = home_score + away_score

            # Se já tem 2+ gols, Over 1.5 já bateu — nada a fazer
            if total_goals >= 2:
                return

            # Calcula tendência do jogo
            analyzer = MatchAnalyzer(match)
            stats = analyzer.generate_full_report()

            if not stats or 'goals' not in stats:
                return

            over_15 = stats['goals'].get('over_15', 0)

            # Filtro: jogo precisa ter tendência Over forte
            if over_15 < self.MIN_OVER_15_PROB:
                return

            # --- Fase 1: Radar (0-20') ---
            if elapsed <= 20:
                self._radar_phase(match, over_15, elapsed)
                return

            # --- Fase 2: Entrada Fracionada (20-45') ---
            # Só entra se o jogo ainda estiver 0x0
            if total_goals == 0:
                self._entry_phase(match, elapsed, over_15)
            else:
                # Tem 1 gol — verifica se precisa alertar LAY (Free Bet)
                self._check_free_bet_layer(match, home_score, away_score, elapsed)

            # --- Fase 3: HT 0x0 ---
            if match.status == 'HT' and total_goals == 0:
                self._ht_hold_phase(match, over_15)

        except Exception as e:
            logger.error(f"Erro ao analisar jogo para Over 1.5 {match.id}: {str(e)}")

    def _radar_phase(self, match, over_15, elapsed):
        """Fase de radar: informa que o jogo é candidato Over."""
        market_key = "TLGRM_OVER_RADAR"
        tip, created = ScannerTip.objects.get_or_create(
            match=match,
            market=market_key,
            defaults={
                'prediction_text': f"Over Radar ({over_15}%)",
                'probability': over_15,
                'status': 'PENDING'
            }
        )
        if not created:
            return  # Já alertamos o radar

        msg = (
            f"📡 <b>RADAR OVER 1.5 (Jogo Promissor)</b>\n\n"
            f"🏆 {match.league.name}\n"
            f"⚽ <b>{match.home_team.name} 0 x 0 {match.away_team.name}</b>\n"
            f"⏱️ <i>{elapsed}' minutos</i>\n\n"
            f"📊 <b>Probabilidade Over 1.5:</b> {over_15}%\n\n"
            f"⏳ <b>Próximo passo:</b> Aguardar a janela de entrada.\n"
            f"🚫 <b>NÃO ENTRE AGORA.</b> Deixe a odd engordar naturalmente.\n"
            f"🔔 Às 20' (se 0x0), enviarei o alerta da 1ª fração.\n\n"
            f"💡 <i>Método Drip Staking: 3 entradas fracionadas (20', 27', 35').</i>"
        )

        logger.info(f"📡 Radar Over 1.5: {match.home_team.name} x {match.away_team.name}")
        self._send(msg)

    def _entry_phase(self, match, elapsed, over_15):
        """Verifica se é hora de cada entrada fracionada (20, 27, 35 min)."""
        entries = {
            20: "TLGRM_OVER_ENTRY_20",
            27: "TLGRM_OVER_ENTRY_27",
            35: "TLGRM_OVER_ENTRY_35",
        }

        entry_minute = None
        market_key = None

        for target_min, key in entries.items():
            if abs(elapsed - target_min) <= self.ENTRY_WINDOW:
                entry_minute = target_min
                market_key = key
                break

        if not market_key:
            return

        # Anti-spam: já enviamos essa entrada?
        tip, created = ScannerTip.objects.get_or_create(
            match=match,
            market=market_key,
            defaults={
                'prediction_text': f"Over Entry {entry_minute}' ({over_15}%)",
                'probability': over_15,
                'status': 'PENDING'
            }
        )
        if not created:
            return

        # Calcula qual fração (1, 2 ou 3)
        if entry_minute == 20:
            fracoes_enviadas = 1
        elif entry_minute == 27:
            fracoes_enviadas = 2
        else:
            fracoes_enviadas = 3

        stake_fracao = self.STAKE_TERCO
        stake_acumulada = round(stake_fracao * fracoes_enviadas, 2)
        odd_media = "↑" if fracoes_enviadas > 1 else "esticando"

        # Títulos e descrições diferentes por fração
        if entry_minute == 20:
            titulo = "1ª FRAÇÃO — HORA DE ENTRAR"
            obs = (f"A odd do Over 1.5 engordou naturalmente. Coloque **R$ {stake_fracao:.2f}** "
                   f"no Over 1.5 agora.\n\n"
                   f"📌 <b>Próxima entrada:</b> 27' (se continuar 0x0).")
        elif entry_minute == 27:
            titulo = "2ª FRAÇÃO — DOSE DO MEIO"
            obs = (f"Já são {elapsed}' e o jogo segue 0x0. A odd está mais gorda.\n"
                   f"Coloque mais **R$ {stake_fracao:.2f}** no Over 1.5.\n\n"
                   f"📌 <b>Stake acumulada:</b> R$ {stake_acumulada:.2f}\n"
                   f"📌 <b>Última entrada:</b> 35' (se continuar 0x0).")
        else:
            titulo = "3ª FRAÇÃO — ÚLTIMA DOSE"
            obs = (f"Aos {elapsed}' e o placar ainda 0x0. Sua **odd média** está altíssima!\n"
                   f"Coloque a última **R$ {stake_fracao:.2f}** no Over 1.5.\n\n"
                   f"📌 <b>Stake total:</b> R$ {stake_acumulada:.2f}\n"
                   f"💰 <b>Retorno potencial:</b> R$ {round(stake_acumulada * 1.50, 2)} (com odd média ~1.50)")

        msg = (
            f"⚡ <b>OVER 1.5 — {titulo}</b>\n\n"
            f"🏆 {match.league.name}\n"
            f"⚽ <b>{match.home_team.name} 0 x 0 {match.away_team.name}</b>\n"
            f"⏱️ <i>{elapsed}' minutos</i>\n\n"
            f"📊 Over 1.5: {over_15}% | Odd média: {odd_media}\n\n"
            f"{obs}\n\n"
            f"🛡️ <b>Se sair gol:</b> Faça LAY no Over 1.5 com o mesmo valor já investido "
            f"(R$ {stake_acumulada:.2f}) — vira Free Bet.\n\n"
            f"💡 <i>Método Drip Staking — Estratégia do Blog.</i>"
        )

        logger.info(f"⚡ Over Entry {entry_minute}' para {match.home_team.name} x {match.away_team.name}")
        self._send(msg)

    def _check_free_bet_layer(self, match, h_score, a_score, elapsed):
        """Verifica se saiu gol durante a fase de entrada e alerta o LAY (Free Bet)."""
        # Se não está na janela de gol durante entrada (20-45'), ignora
        if elapsed < 20 or elapsed > 46:
            return

        total_goals = h_score + a_score
        if total_goals != 1:
            return

        # Já enviamos o alerta de LAY?
        lay_key = "TLGRM_OVER_LAY_GOAL"
        tip, created = ScannerTip.objects.get_or_create(
            match=match,
            market=lay_key,
            defaults={
                'prediction_text': f"Over 1.5 LAY Free Bet ({h_score}x{a_score})",
                'probability': 0,
                'status': 'PENDING'
            }
        )
        if not created:
            return  # Já avisamos

        # Descobre quantas frações foram enviadas (qual stake acumulada)
        entry_keys = ['TLGRM_OVER_ENTRY_20', 'TLGRM_OVER_ENTRY_27', 'TLGRM_OVER_ENTRY_35']
        fracoes = ScannerTip.objects.filter(
            match=match,
            market__in=entry_keys
        ).count()
        stake_acumulada = round(self.STAKE_TERCO * fracoes, 2)

        if fracoes == 0:
            # Nenhuma entrada foi enviada ainda — não precisa alertar LAY
            tip.delete()
            return

        msg = (
            f"⚽ <b>FREE BET — LAY NO OVER 1.5 AGORA</b>\n\n"
            f"🏆 {match.league.name}\n"
            f"⚽ <b>{match.home_team.name} {h_score} x {a_score} {match.away_team.name}</b>\n"
            f"⏱️ <i>{elapsed}' minutos</i>\n\n"
            f"📌 <b>Ação imediata:</b>\n"
            f"Faça um <b>LAY (Aposta Contra)</b> no Over 1.5 com exatamente "
            f"<b>R$ {stake_acumulada:.2f}</b> (valor já investido).\n\n"
            f"📊 <b>Resultado:</b>\n"
            f"✅ Se jogo terminar 1x0 → <b>Lucro 0 / Prejuízo 0</b> (Free Bet)\n"
            f"✅ Se sair o 2º gol → <b>Lucro entra todo na conta!</b>\n\n"
            f"💡 <i>Espere o mercado reabrir e estabilizar (2-3 min após o gol) "
            f"antes de executar o LAY.</i>"
        )

        logger.info(f"⚽ Free Bet LAY para {match.home_team.name} x {match.away_team.name} (stake R$ {stake_acumulada:.2f})")
        self._send(msg)

    def _ht_hold_phase(self, match, over_15):
        """Fase de intervalo: 0x0 segurar, não entrar em pânico."""
        market_key = "TLGRM_OVER_HT_HOLD"
        tip, created = ScannerTip.objects.get_or_create(
            match=match,
            market=market_key,
            defaults={
                'prediction_text': f"Over 1.5 HT Hold ({over_15}%)",
                'probability': over_15,
                'status': 'PENDING'
            }
        )
        if not created:
            return

        # Verifica se alguma entrada foi enviada (para saber se tem posição)
        entry_keys = ['TLGRM_OVER_ENTRY_20', 'TLGRM_OVER_ENTRY_27', 'TLGRM_OVER_ENTRY_35']
        fracoes = ScannerTip.objects.filter(
            match=match,
            market__in=entry_keys
        ).count()
        tem_posicao = fracoes > 0

        if not tem_posicao:
            # Se não entrou, não tem o que segurar
            return

        stake_acumulada = round(self.STAKE_TERCO * fracoes, 2)

        msg = (
            f"🧘 <b>INTERVALO — MANTENHA A CALMA</b>\n\n"
            f"🏆 {match.league.name}\n"
            f"⚽ <b>{match.home_team.name} 0 x 0 {match.away_team.name}</b>\n"
            f"⏱️ <i>Intervalo (45')</i>\n\n"
            f"📊 Over 1.5: {over_15}%\n"
            f"💰 Já investido: <b>R$ {stake_acumulada:.2f}</b>\n\n"
            f"⚠️ <b>O amador entra em pânico e faz Cashout.</b>\n"
            f"✅ <b>O profissional:</b>\n"
            f"• A maioria dos gols do futebol mundial acontece no <b>2º Tempo</b>\n"
            f"• Se a análise pré-jogo estava correta, confie no método\n"
            f"• Mantenha a posição e aguarde\n\n"
            f"💡 <i>Método Drip Staking — A paciência é o diferencial.</i>"
        )

        logger.info(f"🧘 HT Hold: {match.home_team.name} x {match.away_team.name}")
        self._send(msg)