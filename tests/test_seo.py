"""Datos estructurados (Schema.org)."""
from datetime import datetime, timedelta

from gosaria import horario
from gosaria.db import get_db

from .conftest import por_tipo


def _crear_evento(app, dias=7):
    inicio = (horario.ahora() + timedelta(days=dias)).replace(hour=18, minute=0, second=0, microsecond=0, tzinfo=None)
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO eventos (titulo_es, titulo_en, desc_es, inicio, fin) VALUES (?, ?, ?, ?, ?)",
                   ("Taller de latte art", "Latte art workshop", "Aprende a dibujar en el café",
                    inicio.strftime("%Y-%m-%dT%H:%M"), (inicio + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")))
        db.commit()
    return inicio


def test_negocio_en_todas_las_paginas(client):
    for ruta in ("/", "/carta", "/sala-y-eventos", "/el-espacio", "/contacto"):
        negocio = por_tipo(client.get(ruta).get_data(as_text=True), "CafeOrCoffeeShop")
        assert len(negocio) == 1, ruta
        n = negocio[0]
        assert n["address"]["streetAddress"] == "Plaza Salesianos, 8"
        assert n["acceptsReservations"] is False  # las mesas no se reservan
        assert n["openingHoursSpecification"]


def test_cocina_en_el_idioma_de_la_pagina(client):
    es = por_tipo(client.get("/").get_data(as_text=True), "CafeOrCoffeeShop")[0]
    en = por_tipo(client.get("/en/").get_data(as_text=True), "CafeOrCoffeeShop")[0]
    assert "Café de especialidad" in es["servesCuisine"]
    assert "Specialty coffee" in en["servesCuisine"]


def test_menu_en_la_carta(client):
    menu = por_tipo(client.get("/carta").get_data(as_text=True), "Menu")[0]
    items = [i for s in menu["hasMenuSection"] for i in s["hasMenuItem"]]
    assert any(i["name"] == "Huevo poché" and i["offers"]["price"] == "8.50" for i in items)


def test_sala_como_event_venue(client):
    for ruta in ("/sala-y-eventos", "/en/events-space"):
        html = client.get(ruta).get_data(as_text=True)
        sala = por_tipo(html, "EventVenue")
        assert len(sala) == 1, ruta
        assert sala[0]["containedInPlace"]["@id"].endswith("/#negocio")
        assert sala[0]["address"]["streetAddress"] == "Plaza Salesianos, 8"
        negocio = por_tipo(html, "CafeOrCoffeeShop")[0]
        assert negocio["containsPlace"]["@id"] == sala[0]["@id"]


def test_evento_con_zona_horaria(app, client):
    inicio = _crear_evento(app)
    eventos = por_tipo(client.get("/sala-y-eventos").get_data(as_text=True), "Event")
    assert len(eventos) == 1
    ev = eventos[0]
    esperado = inicio.replace(tzinfo=horario.TZ).isoformat()
    assert ev["startDate"] == esperado
    assert ev["startDate"][-6:] in ("+01:00", "+02:00")
    assert datetime.fromisoformat(ev["endDate"]).utcoffset() is not None
    assert ev["location"]["@type"] == "EventVenue"
    assert ev["image"]


def test_evento_en_la_portada(app, client):
    _crear_evento(app)
    html = client.get("/en/").get_data(as_text=True)
    assert por_tipo(html, "Event")[0]["name"] == "Latte art workshop"


def test_aforo_de_la_sala(client, monkeypatch):
    from gosaria.config import NEGOCIO
    monkeypatch.setitem(NEGOCIO, "sala_aforo", "40 personas")
    sala = por_tipo(client.get("/sala-y-eventos").get_data(as_text=True), "EventVenue")[0]
    assert sala["maximumAttendeeCapacity"] == 40
    assert "40 personas" in client.get("/sala-y-eventos").get_data(as_text=True)
