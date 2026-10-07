"""Horario de apertura y estado "abierto ahora" en hora de Pamplona."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .config import NEGOCIO
from .i18n import DIAS, t

TZ = ZoneInfo("Europe/Madrid")


def _hm(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


def hora(valor: time | str) -> str:
    """9:00 en vez de 09:00, como se escribe en español e inglés británico."""
    if isinstance(valor, str):
        valor = _hm(valor)
    return f"{valor.hour}:{valor.minute:02d}"


def franjas(dia: date) -> list[tuple[time, time]]:
    if dia.isoformat() in NEGOCIO["cierres"]:
        return []
    return [(_hm(a), _hm(b)) for a, b in NEGOCIO["horario"].get(dia.weekday(), [])]


def ahora() -> datetime:
    return datetime.now(TZ)


def estado(lang: str, momento: datetime | None = None) -> dict:
    """Devuelve {'abierto': bool, 'texto': '...'} para mostrar en la cabecera."""
    momento = momento or ahora()
    hoy = momento.date()
    actual = momento.time()
    for inicio, fin in franjas(hoy):
        if inicio <= actual < fin:
            return {"abierto": True, "texto": f"{t(lang, 'abierto')} · {t(lang, 'hasta', h=hora(fin))}"}
    for inicio, _ in franjas(hoy):
        if actual < inicio:
            return {"abierto": False, "texto": f"{t(lang, 'cerrado')} · {t(lang, 'abre_hoy', h=hora(inicio))}"}
    for i in range(1, 8):
        dia = hoy + timedelta(days=i)
        fr = franjas(dia)
        if fr:
            h = hora(fr[0][0])
            if i == 1:
                siguiente = t(lang, "abre_manana", h=h)
            else:
                siguiente = t(lang, "abre_dia", d=DIAS[lang][dia.weekday()].lower() if lang == "es" else DIAS[lang][dia.weekday()], h=h)
            return {"abierto": False, "texto": f"{t(lang, 'cerrado')} · {siguiente}"}
    return {"abierto": False, "texto": t(lang, "cerrado")}


def tabla(lang: str, momento: datetime | None = None) -> list[dict]:
    """Filas para la tabla de horario, con el día de hoy marcado."""
    momento = momento or ahora()
    filas = []
    for i, nombre in enumerate(DIAS[lang]):
        fr = NEGOCIO["horario"].get(i, [])
        texto = ", ".join(f"{hora(a)} – {hora(b)}" for a, b in fr) if fr else t(lang, "cerrado_dia")
        filas.append({"dia": nombre, "horas": texto, "hoy": i == momento.weekday()})
    return filas


def horario_js() -> dict:
    """Horario serializable para que el JS actualice el estado sin recargar."""
    return {str(k): v for k, v in NEGOCIO["horario"].items()} | {"cierres": NEGOCIO["cierres"]}


def schema_horario() -> list[dict]:
    """openingHoursSpecification para Schema.org."""
    nombres = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    grupos: dict[tuple, list[str]] = {}
    for dia, fr in NEGOCIO["horario"].items():
        for a, b in fr:
            grupos.setdefault((a, b), []).append(nombres[dia])
    return [
        {"@type": "OpeningHoursSpecification", "dayOfWeek": dias, "opens": a, "closes": b}
        for (a, b), dias in grupos.items()
    ]
