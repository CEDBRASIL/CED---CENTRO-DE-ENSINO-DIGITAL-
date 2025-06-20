import logging
import os
import requests

from utils import formatar_numero_whatsapp

WHATSAPP_URL = os.getenv(
    "WHATSAPP_URL", "https://api.cedbrasilia.com.br/send"
)
WHATSAPP_LOG_NUM = os.getenv("WHATSAPP_LOG_NUM", "556186660241")

class WhatsAppHandler(logging.Handler):
    """Envia logs para o WhatsApp configurado."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        numero = formatar_numero_whatsapp(WHATSAPP_LOG_NUM)
        if not numero:
            return
        mensagem = self.format(record)
        try:
            requests.get(
                WHATSAPP_URL,
                params={"para": numero, "mensagem": mensagem},
                timeout=10,
            )
        except Exception:
            # Evita quebra do logger em caso de falha
            pass

def setup_logging() -> None:
    """Configura o logging padrão e o handler do WhatsApp."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    if os.getenv("DISABLE_WA_LOG", "0") not in ("1", "true", "True"):
        handler = WhatsAppHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logging.getLogger().addHandler(handler)

def send_startup_message() -> None:
    """Envia uma mensagem informando que o servidor iniciou."""
    logging.info("<SERVER ON/>")
