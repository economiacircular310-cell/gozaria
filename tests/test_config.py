"""Configuración desde variables de entorno (.env)."""
import re

from gosaria import config


def test_variable_vacia_usa_el_valor_por_defecto(monkeypatch):
    monkeypatch.setenv("PRUEBA_VACIA", "")
    assert config.env("PRUEBA_VACIA", "por defecto") == "por defecto"
    monkeypatch.setenv("PRUEBA_VACIA", "   ")
    assert config.env("PRUEBA_VACIA", "por defecto") == "por defecto"
    monkeypatch.setenv("PRUEBA_VACIA", " valor ")
    assert config.env("PRUEBA_VACIA", "por defecto") == "valor"


def test_valores_vacios_del_env_demo():
    """deploy/env.demo deja estas variables vacías: deben valer su valor por defecto."""
    assert config.Config.SMTP_PORT == 587
    assert config.Config.MAIL_FROM == "contacto@gosariapamplona.es"
    assert config.NEGOCIO["email"] == "contacto@gosariapamplona.es"
    assert config.TITULAR["domicilio"].startswith("Plaza Salesianos")
    assert config.NEGOCIO["google_resenas"].startswith("https://")


def test_enlace_de_resena_nunca_vacio(client):
    for ruta in ("/", "/en/", "/enlaces", "/en/links"):
        html = client.get(ruta).get_data(as_text=True)
        enlaces = re.findall(r'<a [^>]*href="([^"]*)"[^>]*>(?:Escribir una reseña|Write a review)', html)
        assert enlaces, ruta
        assert all(e.startswith("https://") for e in enlaces), (ruta, enlaces)
