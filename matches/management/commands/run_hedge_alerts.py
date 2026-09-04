from django.core.management.base import BaseCommand
from matches.models import Match, ScannerTip
from matches.services.telegram_bot import TelegramBotService
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Monitora jogos ao vivo e envia alertas de proteção (hedge) no Telegram.'

    # Configurações (Van pode ajustar depois)
    STAKE_UNDER = 40        # Valor médio que Van aposta por Under (R$ 30-50)
    ODD_UNDER = 1.85        # Odd estimada do Under
    ODD_OVER = 3.50         # Odd estimada do Over ao vivo (no momento do perigo)

    # Limiares de perigo
    MIN_TOTAL_GOALS = 4     # A partir de 4 gols, Under 4.5 está em risco
    MIN_ELAPSED = 70        # Só alerta a partir dos 70 minutos (2º tempo)
    MAX_ELAPSED = 95        # Para de alertar depois dos 95 (jogo acabando)

    def handle(self, *args, **options):
        self.stdout.write("🔍 Verificando jogos em perigo para proteção...")

        # Busca jogos ao vivo com 4+ gols no 2º tempo
        perigosos = Match.objects.filter(
            status__in=['2H', 'In Progress', 'Live'],
            home_score__isnull=False,
            away_score__isnull=False,
        ).exclude(
            home_score=None, away_score=None
        ).select_related('home_team', 'away_team', 'league')

        enviados = 0
        for match in perigosos:
            try:
                self._check_match(match)
                enviados += 1
            except Exception as e:
                logger.error(f"Erro ao verificar proteção para jogo {match.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"✅ Verificação concluída. {enviados} jogos analisados."))

    def _check_match(self, match):
        h = match.home_score or 0
        a = match.away_score or 0
        total = h + a
        elapsed = match.elapsed_time or 0

        # Filtro de tempo
        if elapsed < self.MIN_ELAPSED or elapsed > self.MAX_ELAPSED:
            return

        # Filtro de gols: só alerta se tiver 4+ gols (Under 4.5 em risco)
        # ou 5+ gols (Under 5.5 em risco)
        if total < 4:
            return

        # Verifica se esse jogo já teve alerta UNDER antes (só protegemos o que recomendamos)
        teve_alerta_under = ScannerTip.objects.filter(
            match=match,
            market__startswith='TLGRM_UNDER_'
        ).exists()

        if not teve_alerta_under:
            return

        # Define a linha de perigo
        if total == 4:
            linha_under = 4.5
            mercado_over = "Over 4.5"
            mercado_under = "Under 4.5"
        else:
            linha_under = 5.5
            mercado_over = "Over 5.5"
            mercado_under = "Under 5.5"

        # Anti-spam: já enviamos hedge pra esse jogo/linha?
        market_key = f"TLGRM_HEDGE_{int(linha_under*10)}"
        ja_enviado = ScannerTip.objects.filter(
            match=match,
            market=market_key
        ).exists()
        if ja_enviado:
            return

        # Calcula o hedge
        hedge = round(self.STAKE_UNDER * self.ODD_UNDER / self.ODD_OVER)
        lucro_segurar = round(self.STAKE_UNDER * (self.ODD_UNDER - 1) - hedge, 2)
        lucro_estourar = round(hedge * (self.ODD_OVER - 1) - self.STAKE_UNDER, 2)

        # Registra que enviamos
        ScannerTip.objects.create(
            match=match,
            market=market_key,
            probability=0,
            prediction_text=f"Hedge {mercado_under} ({hedge})",
            status='PENDING'
        )

        # Monta a mensagem
        home_name = match.home_team.name
        away_name = match.away_team.name
        league = match.league.name

        msg = (
            f"⚠️ <b>PROTEÇÃO AGORA — {league}</b> ⚠️\n\n"
            f"⚽ <b>{home_name} {h} x {a} {away_name}</b>\n"
            f"⏱️ <i>{elapsed}' minutos</i>\n\n"
            f"🎯 <b>Sua aposta:</b> {mercado_under} (R$ {self.STAKE_UNDER} @ {self.ODD_UNDER})\n"
            f"📉 <b>Perigo:</b> {total} gols já. 1 a mais estoura sua aposta!\n\n"
            f"🛡️ <b>Faça AGORA:</b> R$ {hedge} no <b>{mercado_over}</b> (odd ~{self.ODD_OVER})\n\n"
            f"📊 <b>Resultados possíveis:</b>\n"
            f"✅ Se <b>segurar</b> em {h}x{a}: você ganha <b>+R$ {lucro_segurar}</b>\n"
            f"✅ Se <b>estourar</b> (sair o {total+1}º gol): você ganha <b>+R$ {lucro_estourar}</b>\n\n"
            f"💰 <b>Você não perde em NENHUM cenário.</b>"
        )

        TelegramBotService.send_message(msg)
        logger.info(f"🛡️ Hedge enviado: {home_name} {h}x{a} {away_name} - {mercado_over} R${hedge}")