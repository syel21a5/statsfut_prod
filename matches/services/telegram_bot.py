import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class TelegramBotService:
    @staticmethod
    def send_message(text: str, chat_id: str = None) -> bool:
        """
        Envia uma mensagem de texto para um chat específico via Telegram Bot API.
        Se chat_id não for fornecido, tenta usar o TELEGRAM_CHAT_ID do settings.
        """
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        target_chat_id = chat_id or getattr(settings, 'TELEGRAM_CHAT_ID', None)
        
        if not token or not target_chat_id:
            logger.warning("TelegramBotService: Token ou Chat ID ausente. Mensagem não enviada.")
            return False
            
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Erro ao enviar Telegram: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exceção ao enviar Telegram: {str(e)}")
            return False

    @staticmethod
    def get_updates() -> list:
        """
        Puxa as últimas mensagens recebidas pelo Bot (usado para descobrir o Chat ID).
        """
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not token:
            return []
            
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('result', [])
            return []
        except Exception as e:
            logger.error(f"Exceção ao buscar atualizações do Telegram: {str(e)}")
            return []
