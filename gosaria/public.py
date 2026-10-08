"""Páginas públicas de la web."""
from __future__ import annotations

import json
from datetime import timedelta

from flask import (Blueprint, Response, current_app, g, redirect, render_template,
                   request, send_from_directory)

from . import db, forms, horario, mailer, security, seo
from .config import NEGOCIO
from .contenido import FAQ, PUNTOS_FUERTES
from .i18n import LANGS, NOINDEX, PAGES, SIN_SITEMAP, page_url, t

bp = Blueprint("public", __name__)


@bp.context_processor
def _aviso():
    """El aviso destacado (p. ej. el premio) se muestra en todas las páginas públicas."""
    return {"aviso": db.ajustes()}

# título y descripción de cada página (SEO)
META = {
    "inicio": {
        "es": ("Gosaria · Café de especialidad y brunch en Pamplona",
               "Cafetería de especialidad en la Plaza Salesianos de Pamplona: brunch todo el día, tostadas de masa madre, repostería artesana y sala para eventos. Pet friendly."),
        "en": ("Gosaria · Specialty coffee and brunch in Pamplona",
               "Specialty coffee shop on Plaza Salesianos, Pamplona: all-day brunch, sourdough toasts, homemade pastries and an events room. Dog friendly."),
    },
    "carta": {
        "es": ("Carta · Gosaria Pamplona",
               "Carta de Gosaria con precios: tostadas de masa madre, bowls, sándwiches, ensaladas, smash burgers y bocadillos. Opciones vegetarianas y sin gluten."),
        "en": ("Menu · Gosaria Pamplona",
               "Gosaria's menu with prices: sourdough toasts, bowls, sandwiches, salads, smash burgers and bocadillos. Vegetarian and gluten-free options."),
    },
    "sala": {
        "es": ("Sala para eventos y catering en Pamplona · Gosaria",
               "Alquila la sala de Gosaria en la Plaza Salesianos para cumpleaños, reuniones, cenas y talleres. Desde 25 € la hora, con catering propio. Pide presupuesto."),
        "en": ("Events room and catering in Pamplona · Gosaria",
               "Hire Gosaria's room on Plaza Salesianos for birthdays, meetings, dinners and workshops. From €25 an hour, with our own catering. Request a quote."),
    },
    "espacio": {
        "es": ("El espacio · Gosaria Pamplona",
               "Gosaria es un espacio de conexión en Pamplona: cafetería de especialidad, sala de talleres, exposiciones y productos locales, en un local amplio y luminoso."),
        "en": ("The space · Gosaria Pamplona",
               "Gosaria is a place to connect in Pamplona: specialty café, workshop room, exhibitions and local products, in a bright and spacious venue."),
    },
    "contacto": {
        "es": ("Contacto y horario · Gosaria Pamplona",
               "Horario, dirección y contacto de Gosaria en la Plaza Salesianos 8 de Pamplona. Abrimos todos los días desde las 9:00."),
        "en": ("Contact and opening hours · Gosaria Pamplona",
               "Opening hours, address and contact details for Gosaria at Plaza Salesianos 8, Pamplona. Open every day from 9:00."),
    },
    "enlaces": {
        "es": ("Enlaces · Gosaria", "Carta, sala, cómo llegar y reseñas de Gosaria."),
        "en": ("Links · Gosaria", "Gosaria's menu, events room, directions and reviews."),
    },
    "aviso_legal": {
        "es": ("Aviso legal · Gosaria", "Aviso legal e identificación del titular de gosariapamplona.es."),
        "en": ("Legal notice · Gosaria", "Legal notice and owner details for gosariapamplona.es."),
    },
    "privacidad": {
        "es": ("Política de privacidad · Gosaria", "Cómo trata Gosaria los datos personales que nos envías por la web."),
        "en": ("Privacy policy · Gosaria", "How Gosaria handles the personal data you send us through the website."),
    },
    "cookies": {
        "es": ("Política de cookies · Gosaria", "Qué cookies usa gosariapamplona.es y cómo puedes configurarlas."),
        "en": ("Cookie policy · Gosaria", "Which cookies gosariapamplona.es uses and how to change your settings."),
    },
}


def _meta(page: str, lang: str) -> dict:
    title, description = META[page][lang]
    return {
        "title": title,
        "description": description,
        "canonical": current_app.config["SITE_URL"] + page_url(page, lang),
        "alternates": {l: current_app.config["SITE_URL"] + page_url(page, l) for l in LANGS},
        "noindex": page in NOINDEX or current_app.config["NOINDEX_SITIO"],
    }


def _render(page: str, lang: str, template: str, status: int = 200, **ctx):
    g.lang = lang
    g.page = page
    ctx.setdefault("jsonld", seo.jsonld(seo.negocio(lang)))
    return render_template(template, page=page, meta=_meta(page, lang), **ctx), status


def _migas(lang: str, page: str) -> dict:
    return seo.migas(lang, [(t(lang, "inicio"), page_url("inicio", lang)),
                            (t(lang, f"nav_{page}"), page_url(page, lang))])


def _route(page: str, methods: tuple[str, ...] = ("GET",)):
    """Registra la vista para las rutas ES y EN de una página."""
    def deco(view):
        for lang in LANGS:
            bp.add_url_rule(PAGES[page][lang], endpoint=f"{page}_{lang}", view_func=view,
                            defaults={"lang": lang}, methods=list(methods))
        return view
    return deco


# --- Páginas ------------------------------------------------------------

@_route("inicio")
def inicio(lang):
    momento = horario.ahora()
    ajustes = db.ajustes()
    eventos = db.eventos_proximos(lang, momento.replace(tzinfo=None))[:3]
    return _render(
        "inicio", lang, "inicio.html",
        destacados=db.destacados(lang),
        precio_sala=db.precio_minimo_sala(),
        eventos=eventos,
        ajustes=ajustes,
        puntos=PUNTOS_FUERTES[lang],
        faq=FAQ[lang],
        jsonld=seo.jsonld(seo.negocio(lang), seo.faq(FAQ[lang]), seo.eventos(lang, eventos)),
    )


@_route("carta")
def carta(lang):
    secciones = db.secciones("carta", lang)
    return _render("carta", lang, "carta.html", secciones=secciones,
                   jsonld=seo.jsonld(seo.negocio(lang), seo.menu(lang, secciones), _migas(lang, "carta")))


def _form_ctx(lang: str) -> dict:
    return {"csrf": security.csrf_token(), "timer": security.form_timer()}


def _procesar(tipo: str, lang: str):
    """Valida y guarda un formulario. Devuelve (redirect | None, datos, errores, error_general)."""
    if not security.csrf_valido():
        return None, request.form, {}, t(lang, "e_csrf")
    destino = f"{page_url('sala' if tipo == 'sala' else 'contacto', lang)}?enviado=1#formulario"
    if security.parece_spam():
        return redirect(destino, code=303), {}, {}, None
    if security.limite_superado(f"form-{tipo}", maximo=5, ventana_seg=600):
        return None, request.form, {}, t(lang, "e_rate")
    if tipo == "sala":
        datos, errores = forms.sala(request.form, lang, horario.ahora().date())
    else:
        datos, errores = forms.contacto(request.form, lang)
    if errores:
        return None, datos, errores, t(lang, "f_errores")
    extra = {k: v for k, v in datos.items() if k not in {"nombre", "email", "telefono", "privacidad"}}
    mensaje_id = db.guardar_mensaje(tipo, datos["nombre"], datos["email"], datos["telefono"], extra)
    asunto = (f"Solicitud de sala: {datos['tipo']} el {datos['fecha']} ({datos['personas']} personas)"
              if tipo == "sala" else f"Mensaje de la web de {datos['nombre']}")
    if mailer.enviar(asunto, forms.texto_correo(tipo, datos), datos["email"]):
        db.marcar_enviado(mensaje_id)
    return redirect(destino, code=303), {}, {}, None


@_route("sala", methods=("GET", "POST"))
def sala(lang):
    datos, errores, error_general, status = {}, {}, None, 200
    if request.method == "POST":
        resp, datos, errores, error_general = _procesar("sala", lang)
        if resp:
            return resp
        status = 422
    momento = horario.ahora()
    eventos = db.eventos_proximos(lang, momento.replace(tzinfo=None))
    return _render(
        "sala", lang, "sala.html", status,
        tarifas=db.secciones("tarifas", lang),
        catering=db.secciones("catering", lang),
        precio_sala=db.precio_minimo_sala(),
        eventos=eventos,
        enviado=request.args.get("enviado") == "1",
        datos=datos, errores=errores, error_general=error_general,
        hoy=momento.date().isoformat(),
        jsonld=seo.jsonld(seo.negocio(lang), seo.sala(lang), seo.eventos(lang, eventos), _migas(lang, "sala")),
        **_form_ctx(lang),
    )




@_route("espacio")
def espacio(lang):
    return _render("espacio", lang, "espacio.html",
                   jsonld=seo.jsonld(seo.negocio(lang), _migas(lang, "espacio")))


@_route("contacto", methods=("GET", "POST"))
def contacto(lang):
    datos, errores, error_general, status = {}, {}, None, 200
    if request.method == "POST":
        resp, datos, errores, error_general = _procesar("contacto", lang)
        if resp:
            return resp
        status = 422
    return _render(
        "contacto", lang, "contacto.html", status,
        enviado=request.args.get("enviado") == "1",
        datos=datos, errores=errores, error_general=error_general,
        faq=FAQ[lang],
        jsonld=seo.jsonld(seo.negocio(lang), seo.faq(FAQ[lang]), _migas(lang, "contacto")),
        **_form_ctx(lang),
    )




@_route("enlaces")
def enlaces(lang):
    return _render("enlaces", lang, "enlaces.html", ajustes=db.ajustes())


@_route("aviso_legal")
def aviso_legal(lang):
    return _render("aviso_legal", lang, "legal/aviso_legal.html")


@_route("privacidad")
def privacidad(lang):
    return _render("privacidad", lang, "legal/privacidad.html")


@_route("cookies")
def cookies(lang):
    return _render("cookies", lang, "legal/cookies.html")


# --- Archivos técnicos ---------------------------------------------------

@bp.route("/robots.txt")
def robots():
    url = current_app.config["SITE_URL"]
    if current_app.config["NOINDEX_SITIO"]:
        # Demo: se permite rastrear para que Google vea el noindex de cada página
        return Response("User-agent: *\nAllow: /\nDisallow: /admin\n", mimetype="text/plain")
    texto = "User-agent: *\nAllow: /\nDisallow: /admin\n\n" \
            f"Sitemap: {url}/sitemap.xml\n"
    return Response(texto, mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap():
    url = current_app.config["SITE_URL"]
    hoy = horario.ahora().date().isoformat()
    partes = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
              'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for page, rutas in PAGES.items():
        if page in NOINDEX or page in SIN_SITEMAP:
            continue
        for lang in LANGS:
            partes.append("<url>")
            partes.append(f"<loc>{url}{rutas[lang]}</loc>")
            partes.append(f"<lastmod>{hoy}</lastmod>")
            for alt in LANGS:
                partes.append(f'<xhtml:link rel="alternate" hreflang="{alt}" href="{url}{rutas[alt]}"/>')
            partes.append(f'<xhtml:link rel="alternate" hreflang="x-default" href="{url}{rutas["es"]}"/>')
            partes.append("</url>")
    partes.append("</urlset>")
    return Response("\n".join(partes), mimetype="application/xml")


@bp.route("/manifest.webmanifest")
def manifest():
    data = {
        "name": "Gosaria · Café de especialidad y brunch",
        "short_name": "Gosaria",
        "lang": "es",
        "start_url": "/",
        "display": "browser",
        "background_color": "#ffffff",
        "theme_color": "#ad2687",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/static/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/manifest+json")


@bp.route("/favicon.ico")
def favicon():
    return send_from_directory(current_app.static_folder, "favicon.ico", max_age=int(timedelta(days=30).total_seconds()))


@bp.route("/healthz")
def healthz():
    return {"ok": True, "abierto": horario.estado("es")["abierto"], "negocio": NEGOCIO["nombre"]}
