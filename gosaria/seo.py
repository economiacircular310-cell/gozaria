"""Datos estructurados (Schema.org en JSON-LD) para Google."""
from __future__ import annotations

import json
import re
from datetime import datetime

from markupsafe import Markup

from .config import NEGOCIO, Config
from .horario import TZ, schema_horario
from .i18n import PAGES

URL = Config.SITE_URL
ID_NEGOCIO = "/#negocio"
ID_SALA = PAGES["sala"]["es"] + "#sala"


def _abs(path: str) -> str:
    return URL + path


def _direccion() -> dict:
    d = NEGOCIO["direccion"]
    return {
        "@type": "PostalAddress",
        "streetAddress": d["calle"],
        "postalCode": d["cp"],
        "addressLocality": d["ciudad"],
        "addressRegion": d["provincia"],
        "addressCountry": d["pais"],
    }


def _geo() -> dict:
    return {"@type": "GeoCoordinates", "latitude": NEGOCIO["geo"]["lat"], "longitude": NEGOCIO["geo"]["lng"]}


def _fecha(dt: datetime) -> str:
    """Fecha ISO 8601 con la zona horaria de Pamplona (+01:00 o +02:00 según el horario de verano)."""
    return (dt if dt.tzinfo else dt.replace(tzinfo=TZ)).isoformat()


def negocio(lang: str) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "CafeOrCoffeeShop",
        "@id": _abs(ID_NEGOCIO),
        "name": "Gosaria",
        "alternateName": "Gosaria Pamplona · Espacio de conexión",
        "description": (
            "Cafetería de especialidad con brunch todo el día, repostería artesana y sala para eventos en Pamplona."
            if lang == "es" else
            "Specialty coffee shop with all-day brunch, homemade pastries and an events room in Pamplona."
        ),
        "url": _abs(PAGES["inicio"][lang]),
        "image": [_abs("/static/og-image.jpg"), _abs("/static/img/salon-1280.webp")],
        "logo": _abs("/static/icon-512.png"),
        "email": NEGOCIO["email"],
        "priceRange": NEGOCIO["rango_precio"],
        "servesCuisine": (["Café de especialidad", "Brunch", "Repostería"] if lang == "es"
                          else ["Specialty coffee", "Brunch", "Pastries"]),
        "acceptsReservations": False,
        "hasMenu": _abs(PAGES["carta"][lang]),
        "address": _direccion(),
        "geo": _geo(),
        "hasMap": NEGOCIO["google_maps"],
        "containsPlace": {"@id": _abs(ID_SALA)},
        "openingHoursSpecification": schema_horario(),
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": "Pet friendly", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Wheelchair accessible", "value": True},
        ],
        "sameAs": [u for u in (NEGOCIO["instagram"], NEGOCIO["facebook"], NEGOCIO["tiktok"]) if u],
    }
    if NEGOCIO["telefono"]:
        data["telephone"] = NEGOCIO["telefono"]
    return data


def sala(lang: str) -> dict:
    """La sala anexa como EventVenue, dentro de la cafetería."""
    data = {
        "@context": "https://schema.org",
        "@type": "EventVenue",
        "@id": _abs(ID_SALA),
        "name": "Sala de Gosaria" if lang == "es" else "Gosaria events room",
        "description": (
            "Sala anexa a la cafetería, con mesas amarillas y grandes ventanales, para cumpleaños, reuniones, "
            "cenas, talleres, clases y exposiciones. Se alquila por horas, con catering propio."
            if lang == "es" else
            "A room next to the café, with yellow tables and large windows, for birthdays, meetings, dinners, "
            "workshops, classes and exhibitions. Hired by the hour, with our own catering."
        ),
        "url": _abs(PAGES["sala"][lang]),
        "image": [_abs("/static/img/sala-1081.webp"), _abs("/static/img/taller-1280.webp")],
        "address": _direccion(),
        "geo": _geo(),
        "containedInPlace": {"@id": _abs(ID_NEGOCIO)},
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": "Wheelchair accessible", "value": True},
        ],
    }
    aforo = re.match(r"\s*(\d+)", NEGOCIO["sala_aforo"] or "")
    if aforo:
        data["maximumAttendeeCapacity"] = int(aforo.group(1))
    return data


def menu(lang: str, secciones: list[dict]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Menu",
        "name": "Carta de Gosaria" if lang == "es" else "Gosaria menu",
        "inLanguage": lang,
        "url": _abs(PAGES["carta"][lang]),
        "hasMenuSection": [
            {
                "@type": "MenuSection",
                "name": s["nombre"],
                "hasMenuItem": [
                    {
                        "@type": "MenuItem",
                        "name": p["nombre"],
                        **({"description": p["desc"]} if p["desc"] else {}),
                        **({"offers": {"@type": "Offer", "price": f"{p['precio_cent'] / 100:.2f}",
                                       "priceCurrency": "EUR"}} if p["precio_cent"] is not None else {}),
                        **({"suitableForDiet": "https://schema.org/VegetarianDiet"} if p["vegetariano"] else {}),
                    }
                    for p in s["platos"]
                ],
            }
            for s in secciones if s["platos"]
        ],
    }


def faq(preguntas: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in preguntas
        ],
    }


def migas(lang: str, items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": nombre, "item": _abs(path)}
            for i, (nombre, path) in enumerate(items)
        ],
    }


def eventos(lang: str, lista: list[dict]) -> list[dict]:
    lugar = {
        "@type": "EventVenue",
        "@id": _abs(ID_SALA),
        "name": "Sala de Gosaria" if lang == "es" else "Gosaria events room",
        "address": _direccion(),
    }
    return [
        {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": e["titulo"],
            "description": e["desc"],
            "startDate": _fecha(e["inicio"]),
            **({"endDate": _fecha(e["fin"])} if e["fin"] else {}),
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "eventStatus": "https://schema.org/EventScheduled",
            "image": [_abs("/static/img/taller-1280.webp")],
            "location": lugar,
            "organizer": {"@type": "Organization", "name": "Gosaria", "url": URL},
        }
        for e in lista
    ]


def jsonld(*bloques) -> Markup:
    """Devuelve los <script type="application/ld+json"> listos para la plantilla."""
    salida = []
    for b in bloques:
        for item in (b if isinstance(b, list) else [b]):
            texto = json.dumps(item, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
            salida.append(f'<script type="application/ld+json">{texto}</script>')
    return Markup("\n".join(salida))
