from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


def enviar_email(destino: str, assunto: str, mensagem: str) -> bool:
    logger.info("Enviar email para %s: %s", destino, assunto)
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    if not smtp_host or not smtp_user or not smtp_pass:
        logger.warning("SMTP não configurado; a mensagem será apenas registada em log")
        logger.info("Assunto: %s\n%s", assunto, mensagem)
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"] = smtp_user
        msg["To"] = destino
        msg.set_content(mensagem)
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
        return True
    except Exception as exc:
        logger.exception("Falha ao enviar email: %s", exc)
        return False


def enviar_sms(telefone: str, mensagem: str) -> bool:
    logger.info("Enviar SMS para %s", telefone)
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM")
    if not account_sid or not auth_token or not from_number:
        logger.warning("Twilio não configurado; SMS será apenas registado em log")
        logger.info("SMS para %s: %s", telefone, mensagem)
        return False
    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        message = client.messages.create(body=mensagem, from_=from_number, to=telefone)
        logger.info("SMS enviado SID=%s", getattr(message, "sid", None))
        return True
    except Exception as exc:
        logger.exception("Falha ao enviar SMS: %s", exc)
        return False


def notificar_usuario(email: Optional[str], telefone: Optional[str], mensagem: str) -> bool:
    # Preferir email se ambos fornecidos
    if email:
        return enviar_email(email, "Notificação de senha", mensagem)
    if telefone:
        return enviar_sms(telefone, mensagem)
    logger.info("Sem contacto para notificar; mensagem: %s", mensagem)
    return False
