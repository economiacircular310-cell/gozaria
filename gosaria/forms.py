"""Validación de los formularios públicos (contacto y presupuesto de sala)."""
from __future__ import annotations

import re
from datetime import date

from .i18n import t

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
TEL_RE = re.compile(r"^[0-9 +().-]{6,20}$")


def _limpio(form, campo: str, maximo: int) -> str:
    valor = (form.get(campo) or "").strip()
    if campo != "mensaje":  # campos de una línea: sin saltos (evita inyección en cabeceras de correo)
        valor = " ".join(valor.split())
    return valor[:maximo + 1]


def _comunes(form, lang: str) -> tuple[dict, dict]:
    datos = {
        "nombre": _limpio(form, "nombre", 120),
        "email": _limpio(form, "email", 200),
        "telefono": _limpio(form, "telefono", 30),
        "mensaje": _limpio(form, "mensaje", 3000),
        "privacidad": form.get("privacidad") == "1",
    }
    errores = {}
    if not datos["nombre"]:
        errores["nombre"] = t(lang, "e_required")
    elif len(datos["nombre"]) > 120:
        errores["nombre"] = t(lang, "e_too_long")
    if not EMAIL_RE.match(datos["email"]) or len(datos["email"]) > 200:
        errores["email"] = t(lang, "e_email")
    if datos["telefono"] and not TEL_RE.match(datos["telefono"]):
        errores["telefono"] = "Escribe solo números, espacios o +." if lang == "es" else "Use only digits, spaces or +."
    if len(datos["mensaje"]) > 3000:
        errores["mensaje"] = t(lang, "e_too_long")
    if not datos["privacidad"]:
        errores["privacidad"] = t(lang, "e_privacy")
    return datos, errores


def contacto(form, lang: str) -> tuple[dict, dict]:
    datos, errores = _comunes(form, lang)
    if not datos["mensaje"]:
        errores["mensaje"] = t(lang, "e_required")
    return datos, errores


def sala(form, lang: str, hoy: date) -> tuple[dict, dict]:
    datos, errores = _comunes(form, lang)
    tipos = t(lang, "tipos")
    datos.update({
        "fecha": _limpio(form, "fecha", 10),
        "hora": _limpio(form, "hora", 5),
        "duracion": _limpio(form, "duracion", 3),
        "personas": _limpio(form, "personas", 3),
        "tipo": _limpio(form, "tipo", 60),
        "catering": form.get("catering") == "si",
    })
    try:
        if date.fromisoformat(datos["fecha"]) < hoy:
            errores["fecha"] = t(lang, "e_date")
    except ValueError:
        errores["fecha"] = t(lang, "e_date")
    if datos["hora"] and not re.match(r"^\d{2}:\d{2}$", datos["hora"]):
        errores["hora"] = t(lang, "e_required")
    for campo, maximo in (("personas", 200), ("duracion", 24)):
        valor = datos[campo]
        if campo == "personas" or valor:
            if not valor.isdigit() or not 1 <= int(valor) <= maximo:
                errores[campo] = t(lang, "e_number") if campo == "personas" else (
                    "Escribe un número de horas entre 1 y 24." if lang == "es" else "Enter between 1 and 24 hours.")
    if datos["tipo"] not in tipos:
        errores["tipo"] = t(lang, "e_required")
    return datos, errores


def texto_correo(tipo: str, datos: dict) -> str:
    """Cuerpo del correo que recibe Gosaria."""
    lineas = [
        f"Nombre: {datos['nombre']}",
        f"Correo: {datos['email']}",
        f"Teléfono: {datos.get('telefono') or '—'}",
    ]
    if tipo == "sala":
        lineas += [
            f"Fecha: {datos['fecha']}",
            f"Hora de inicio: {datos.get('hora') or '—'}",
            f"Duración: {datos.get('duracion') or '—'} h",
            f"Personas: {datos['personas']}",
            f"Tipo de evento: {datos['tipo']}",
            f"Catering: {'sí' if datos['catering'] else 'no'}",
        ]
    lineas += ["", "Mensaje:", datos.get("mensaje") or "—", "",
               "Enviado desde el formulario de gosariapamplona.es. Responde a este correo para contestar."]
    return "\n".join(lineas)
