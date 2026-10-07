"""Envío de los formularios por correo (SMTP de Microsoft 365).

Si no hay SMTP configurado, el mensaje solo se guarda en la base de datos y
se puede leer en /admin/mensajes.
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from flask import current_app


def enviar(asunto: str, cuerpo: str, responder_a: str) -> bool:
    cfg = current_app.config
    if not (cfg["SMTP_HOST"] and cfg["SMTP_USER"] and cfg["SMTP_PASSWORD"]):
        current_app.logger.info("SMTP sin configurar; mensaje guardado solo en la base de datos.")
        return False
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = formataddr(("Web Gosaria", cfg["MAIL_FROM"]))
    msg["To"] = cfg["MAIL_TO"]
    msg["Reply-To"] = responder_a
    msg["Message-ID"] = make_msgid(domain="gosariapamplona.es")
    msg.set_content(cuerpo)
    try:
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
            smtp.send_message(msg)
        return True
    except Exception:  # noqa: BLE001 - el formulario no debe fallar por el correo
        current_app.logger.exception("No se pudo enviar el correo del formulario")
        return False
