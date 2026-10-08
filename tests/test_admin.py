"""Panel de gestión /admin."""
from datetime import datetime

from gosaria import horario
from gosaria.db import get_db

from .conftest import csrf


def test_requiere_login(client):
    resp = client.get("/admin/carta")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


def test_clave_incorrecta(client):
    client.get("/admin/login")
    resp = client.post("/admin/login", data={"clave": "mala", "csrf": csrf(client)})
    assert resp.status_code == 401


def test_login_sin_csrf(client):
    client.get("/admin/login")
    assert client.post("/admin/login", data={"clave": "x", "csrf": "falso"}).status_code == 400


def test_panel_con_cabeceras_privadas(admin):
    resp = admin.get("/admin")
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "no-store"
    assert resp.headers["X-Robots-Tag"] == "noindex, nofollow"


def _categoria_carta(app) -> int:
    with app.app_context():
        return get_db().execute("SELECT id FROM categorias WHERE slug = 'bowls'").fetchone()[0]


def test_crear_editar_y_borrar_plato(app, admin):
    cat = _categoria_carta(app)
    datos = {"csrf": csrf(admin), "nombre_es": "Bowl de prueba", "nombre_en": "Test bowl",
             "precio": "6,50", "vegetariano": "1", "visible": "1", "orden": ""}
    assert admin.post(f"/admin/plato/nuevo?categoria={cat}", data=datos).status_code == 302
    with app.app_context():
        fila = get_db().execute("SELECT id, precio_cent FROM platos WHERE nombre_es = 'Bowl de prueba'").fetchone()
    assert fila["precio_cent"] == 650
    assert "Bowl de prueba" in admin.get("/carta").get_data(as_text=True)

    admin.post(f"/admin/plato/{fila['id']}", data={**datos, "precio": "7", "visible": ""})
    assert "Bowl de prueba" not in admin.get("/carta").get_data(as_text=True)  # oculto

    admin.post(f"/admin/plato/{fila['id']}/borrar", data={"csrf": csrf(admin)})
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM platos WHERE id = ?", (fila["id"],)).fetchone()[0] == 0


def test_orden_no_numerico_no_rompe_el_panel(app, admin):
    cat = _categoria_carta(app)
    resp = admin.post(f"/admin/plato/nuevo?categoria={cat}", data={
        "csrf": csrf(admin), "nombre_es": "Plato", "orden": "primero"})
    assert resp.status_code == 200
    assert "El orden debe ser un número entero" in resp.get_data(as_text=True)

    resp = admin.post(f"/admin/categoria/{cat}", data={"csrf": csrf(admin), "nombre_es": "Bowls", "orden": "2,5"})
    assert resp.status_code == 200
    assert "El orden debe ser un número entero" in resp.get_data(as_text=True)


def test_precio_no_numerico(app, admin):
    cat = _categoria_carta(app)
    resp = admin.post(f"/admin/plato/nuevo?categoria={cat}", data={
        "csrf": csrf(admin), "nombre_es": "Plato", "precio": "barato"})
    assert resp.status_code == 200
    assert "El precio debe ser un número" in resp.get_data(as_text=True)


def test_el_panel_usa_la_hora_de_pamplona(app, admin, monkeypatch):
    """Un evento que ya ha empezado en Pamplona no cuenta como próximo, aunque el servidor esté en UTC."""
    fijo = datetime(2030, 1, 1, 12, 0, tzinfo=horario.TZ)
    monkeypatch.setattr(horario, "ahora", lambda: fijo)
    for inicio in ("2030-01-01T11:30", "2030-01-01T12:30"):
        admin.post("/admin/evento/nuevo", data={"csrf": csrf(admin), "titulo_es": f"Taller {inicio}",
                                                 "inicio": inicio, "visible": "1"})
    html = admin.get("/admin").get_data(as_text=True)
    assert "<strong>1</strong><span>eventos próximos</span>" in html

    agenda = admin.get("/admin/agenda").get_data(as_text=True)
    assert agenda.count("Pasado") == 1


def test_mensaje_guardado_con_hora_de_pamplona(app, monkeypatch):
    fijo = datetime(2030, 7, 1, 9, 15, tzinfo=horario.TZ)
    monkeypatch.setattr(horario, "ahora", lambda: fijo)
    with app.app_context():
        from gosaria import db
        mid = db.guardar_mensaje("contacto", "Ane", "ane@example.com", "", {})
        creado = db.get_db().execute("SELECT creado FROM mensajes WHERE id = ?", (mid,)).fetchone()[0]
    assert creado == "2030-07-01T09:15:00"


def test_aviso_rechaza_enlace_inseguro(admin):
    resp = admin.post("/admin/aviso", data={"csrf": csrf(admin), "aviso_enlace": "javascript:alert(1)"},
                      follow_redirects=True)
    assert "No se ha guardado" in resp.get_data(as_text=True)
