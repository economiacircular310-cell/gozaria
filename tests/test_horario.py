"""Horario y estado «abierto ahora» (hora de Pamplona)."""
from datetime import datetime

from gosaria import horario


def _en(texto: str) -> datetime:
    return datetime.fromisoformat(texto).replace(tzinfo=horario.TZ)


def test_abierto_entre_semana():
    e = horario.estado("es", _en("2026-10-07T10:00"))  # miércoles
    assert e == {"abierto": True, "texto": "Abierto ahora · hasta las 21:00"}


def test_viernes_hasta_las_23():
    assert horario.estado("en", _en("2026-10-09T22:30"))["texto"] == "Open now · until 23:00"


def test_cerrado_antes_de_abrir():
    assert horario.estado("es", _en("2026-10-07T08:00"))["texto"] == "Cerrado ahora · abrimos hoy a las 9:00"


def test_domingo_por_la_tarde():
    assert horario.estado("es", _en("2026-10-11T16:00"))["texto"] == "Cerrado ahora · abrimos mañana a las 9:00"


def test_cierre_excepcional(monkeypatch):
    monkeypatch.setitem(horario.NEGOCIO, "cierres", ["2026-12-25"])
    e = horario.estado("es", _en("2026-12-25T10:00"))
    assert e["abierto"] is False
    assert "mañana" in e["texto"]


def test_horario_schema():
    filas = {tuple(f["dayOfWeek"]): (f["opens"], f["closes"]) for f in horario.schema_horario()}
    assert filas[("Friday", "Saturday")] == ("09:00", "23:00")
    assert filas[("Sunday",)] == ("09:00", "15:00")
