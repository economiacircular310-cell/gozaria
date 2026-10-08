"""Configuración común de las pruebas.

Las variables de entorno se fijan antes de importar la app, porque config.py
las lee al importarse. Se reproducen los valores vacíos de deploy/env.demo
(NEGOCIO_GOOGLE_RESENA=, SMTP_PORT=...) para probar que la web los tolera.
"""
from __future__ import annotations

import os
import re
import secrets
import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

os.environ.update({
    "GOSARIA_ENV": "development",
    "SECRET_KEY": "clave-solo-para-pruebas",
    "SITE_URL": "https://gosariapamplona.es",
    "NOINDEX_SITIO": "",
    "ADMIN_PASSWORD": "",
    "ADMIN_PASSWORD_HASH": "",
    "SMTP_HOST": "",
    "SMTP_PORT": "",
    "SMTP_USER": "",
    "SMTP_PASSWORD": "",
    "MAIL_FROM": "",
    "MAIL_TO": "",
    "GA_MEASUREMENT_ID": "",
    "NEGOCIO_EMAIL": "",
    "NEGOCIO_TELEFONO": "",
    "NEGOCIO_WHATSAPP": "",
    "NEGOCIO_GLOVO": "",
    "NEGOCIO_GOOGLE_RESENA": "",
    "NEGOCIO_CIERRES": "",
    "SALA_AFORO": "",
    "TITULAR_DOMICILIO": "",
    "TITULAR_EMAIL": "",
})

from gosaria import create_app, security  # noqa: E402

CLAVE_ADMIN = "clave-de-prueba"


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "pruebas.sqlite3"),
        "ADMIN_PASSWORD": CLAVE_ADMIN,
    })
    security.reiniciar_limites()
    yield app
    security.reiniciar_limites()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin(client):
    client.get("/admin/login")
    resp = client.post("/admin/login", data={"clave": CLAVE_ADMIN, "csrf": csrf(client)})
    assert resp.status_code == 302
    return client


def csrf(client) -> str:
    """Token CSRF de la sesión (el login la reinicia, así que se crea si falta)."""
    with client.session_transaction() as s:
        return s.setdefault("csrf", secrets.token_urlsafe(32))


def timer_antiguo(app, segundos: int = 60) -> str:
    """Temporizador del antispam firmado como si el formulario se abriera hace un rato."""
    with app.app_context():
        return security._serializer().dumps(int(time.time()) - segundos)


def enviar_formulario(client, app, url: str, datos: dict, **extra):
    client.get(url)
    campos = {"csrf": csrf(client), "t": timer_antiguo(app), "web": "", **datos, **extra}
    return client.post(url, data=campos)


def jsonld(html: str) -> list[dict]:
    import json
    return [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


def por_tipo(html: str, tipo: str) -> list[dict]:
    return [b for b in jsonld(html) if b.get("@type") == tipo]
