"""Datos estructurados (Schema.org en JSON-LD) para Google."""
from __future__ import annotations

import json

from markupsafe import Markup

from .config import NEGOCIO, Config
from .horario import schema_horario
from .i18n import PAGES

URL = Config.SITE_URL


def _abs(path: str) -> str:
    return URL + path


def negocio(lang: str) -> dict:
    d = NEGOCIO["direccion"]
    data = {
        "@context": "https://schema.org",
        "@type": "CafeOrCoffeeShop",
        "@id": _abs("/#negocio"),
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
        "servesCuisine": ["Café de especialidad", "Brunch", "Repostería"],
        "acceptsReservations": False,
        "hasMenu": _abs(PAGES["carta"][lang]),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": d["calle"],
            "postalCode": d["cp"],
            "addressLocality": d["ciudad"],
            "addressRegion": d["provincia"],
            "addressCountry": d["pais"],
        },
        "geo": {"@type": "GeoCoordinates", "latitude": NEGOCIO["geo"]["lat"], "longitude": NEGOCIO["geo"]["lng"]},
        "hasMap": NEGOCIO["google_maps"],
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
    d = NEGOCIO["direccion"]
    return [
        {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": e["titulo"],
            "description": e["desc"],
            "startDate": e["inicio"].isoformat(),
            **({"endDate": e["fin"].isoformat()} if e["fin"] else {}),
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "eventStatus": "https://schema.org/EventScheduled",
            "location": {
                "@type": "Place",
                "name": "Gosaria",
                "address": {"@type": "PostalAddress", "streetAddress": d["calle"], "postalCode": d["cp"],
                            "addressLocality": d["ciudad"], "addressCountry": d["pais"]},
            },
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
