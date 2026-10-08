"""Formularios de contacto y de presupuesto de la sala."""
from datetime import timedelta

import pytest

from gosaria import horario
from gosaria.db import get_db

from .conftest import csrf, enviar_formulario

CONTACTO = {"nombre": "Ane", "email": "ane@example.com", "mensaje": "Hola", "privacidad": "1"}


def sala_valida():
    manana = (horario.ahora().date() + timedelta(days=1)).isoformat()
    return {"nombre": "Ane", "email": "ane@example.com", "fecha": manana, "personas": "12",
            "tipo": "Cumpleaños o celebración", "catering": "si", "privacidad": "1"}


def mensajes(app):
    with app.app_context():
        return get_db().execute("SELECT tipo, nombre FROM mensajes").fetchall()


@pytest.mark.parametrize("ruta", ["/contacto", "/en/contact", "/sala-y-eventos", "/en/events-space"])
def test_el_formulario_aparece_una_sola_vez(client, ruta):
    html = client.get(ruta).get_data(as_text=True)
    assert html.count("<form") == 1
    assert "<noscript>" not in html and "<template" not in html


def test_contacto_correcto(app, client):
    resp = enviar_formulario(client, app, "/contacto", CONTACTO)
    assert resp.status_code == 303
    assert resp.headers["Location"].endswith("/contacto?enviado=1#formulario")
    assert [tuple(m) for m in mensajes(app)] == [("contacto", "Ane")]
    assert "Hemos recibido tu mensaje" in client.get("/contacto?enviado=1").get_data(as_text=True)


def test_contacto_con_errores(app, client):
    resp = enviar_formulario(client, app, "/contacto", {**CONTACTO, "email": "no-es-un-correo", "privacidad": ""})
    html = resp.get_data(as_text=True)
    assert resp.status_code == 422
    assert html.count("<form") == 1
    assert 'id="e-email"' in html and 'id="e-privacidad"' in html
    assert 'value="Ane"' in html  # conserva lo escrito
    assert mensajes(app) == []


def test_campo_trampa(app, client):
    resp = enviar_formulario(client, app, "/contacto", CONTACTO, web="http://spam.example")
    assert resp.status_code == 303  # el bot cree que ha funcionado
    assert mensajes(app) == []


def test_envio_demasiado_rapido(app, client):
    client.get("/contacto")
    with app.app_context():
        from gosaria import security
        recien = security.form_timer()
    resp = client.post("/contacto", data={**CONTACTO, "csrf": csrf(client), "t": recien})
    assert resp.status_code == 303
    assert mensajes(app) == []


def test_sin_csrf(app, client):
    client.get("/contacto")
    resp = client.post("/contacto", data={**CONTACTO, "csrf": "falso"})
    assert resp.status_code == 422
    assert "La página ha caducado" in resp.get_data(as_text=True)


def test_limite_de_envios(app, client):
    for _ in range(5):
        assert enviar_formulario(client, app, "/contacto", CONTACTO).status_code == 303
    resp = enviar_formulario(client, app, "/contacto", CONTACTO)
    assert resp.status_code == 422
    assert "varios mensajes seguidos" in resp.get_data(as_text=True)


def test_sala_correcta(app, client):
    resp = enviar_formulario(client, app, "/sala-y-eventos", sala_valida())
    assert resp.status_code == 303
    assert resp.headers["Location"].endswith("/sala-y-eventos?enviado=1#formulario")
    assert [tuple(m) for m in mensajes(app)] == [("sala", "Ane")]


@pytest.mark.parametrize("campo, valor", [
    ("fecha", "2020-01-01"),
    ("fecha", "mañana"),
    ("personas", "0"),
    ("personas", "500"),
    ("duracion", "30"),
    ("tipo", "Boda secreta"),
    ("hora", "25h"),
])
def test_sala_valida_cada_campo(app, client, campo, valor):
    resp = enviar_formulario(client, app, "/sala-y-eventos", {**sala_valida(), campo: valor})
    assert resp.status_code == 422
    assert f'id="e-{campo}"' in resp.get_data(as_text=True)
    assert mensajes(app) == []


def test_sala_en_ingles(app, client):
    datos = {**sala_valida(), "tipo": "Business meeting"}
    resp = enviar_formulario(client, app, "/en/events-space", datos)
    assert resp.status_code == 303
    assert resp.headers["Location"].endswith("/en/events-space?enviado=1#formulario")
