"""Web de Gosaria Pamplona (Flask)."""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from flask import Flask, g, redirect, render_template, request
from flask_compress import Compress
from markupsafe import Markup

from . import db, horario, security
from .config import NEGOCIO, TITULAR, Config
from .contenido import alt as foto_alt
from .i18n import DEFAULT_LANG, LEGACY_REDIRECTS, PAGES, other_lang, page_url, t

STATIC_DIR = Path(__file__).resolve().parent / "static"
_hash_cache: dict[str, str] = {}
_css_cache: dict[str, str] = {}


def _static_hash(filename: str) -> str:
    if filename not in _hash_cache:
        ruta = STATIC_DIR / filename
        _hash_cache[filename] = hashlib.sha256(ruta.read_bytes()).hexdigest()[:10] if ruta.exists() else "0"
    return _hash_cache[filename]


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    if app.config["PRODUCTION"] and not app.config["SECRET_KEY_CONFIGURADA"]:
        raise RuntimeError("Falta SECRET_KEY en el archivo .env (obligatoria en producción)")

    app.config["TEMPLATES_AUTO_RELOAD"] = not app.config["PRODUCTION"]
    Compress(app)
    db.init_db(app)
    security.install_headers(app)

    from .admin import bp as admin_bp
    from .public import bp as public_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    _plantillas(app)
    _redirecciones(app)
    _errores(app)
    return app


def lang_actual() -> str:
    return getattr(g, "lang", None) or ("en" if request.path.startswith("/en") else DEFAULT_LANG)


def _plantillas(app: Flask) -> None:
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    def static_v(filename: str) -> str:
        return f"/static/{filename}?v={_static_hash(filename)}"

    def css_en_linea() -> Markup:
        if not app.config["PRODUCTION"] or "css" not in _css_cache:
            _css_cache["css"] = (STATIC_DIR / "css" / "site.css").read_text(encoding="utf-8")
        return Markup(_css_cache["css"])

    def precio(cent: int | None, lang: str) -> str:
        if cent is None:
            return t(lang, "precio_consultar")
        euros = cent / 100
        if lang == "es":
            texto = f"{euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"{texto} €"
        return f"€{euros:,.2f}"

    def precio_corto(cent: int | None, lang: str) -> str:
        """25 € en vez de 25,00 € cuando no hay céntimos."""
        if cent is not None and cent % 100 == 0:
            return f"{cent // 100} €" if lang == "es" else f"€{cent // 100}"
        return precio(cent, lang)

    def fecha_larga(dt: datetime, lang: str) -> str:
        meses = {
            "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                   "septiembre", "octubre", "noviembre", "diciembre"],
            "en": ["January", "February", "March", "April", "May", "June", "July", "August",
                   "September", "October", "November", "December"],
        }[lang]
        from .i18n import DIAS
        dia = DIAS[lang][dt.weekday()]
        if lang == "es":
            return f"{dia.lower()} {dt.day} de {meses[dt.month - 1]} · {dt:%H:%M}"
        return f"{dia}, {dt.day} {meses[dt.month - 1]} · {dt:%H:%M}"

    manifest_cache: dict = {}

    def foto(nombre: str) -> dict:
        if "m" not in manifest_cache:
            import json
            manifest_cache["m"] = json.loads((STATIC_DIR / "img" / "manifest.json").read_text(encoding="utf-8"))
        return manifest_cache["m"][nombre]

    app.jinja_env.globals.update(
        t=t,
        page_url=page_url,
        other_lang=other_lang,
        PAGES=PAGES,
        NEGOCIO=NEGOCIO,
        TITULAR=TITULAR,
        static_v=static_v,
        css_en_linea=css_en_linea,
        csrf_token=security.csrf_token,
        csp_nonce=security.nonce,
        precio=precio,
        precio_corto=precio_corto,
        fecha_larga=fecha_larga,
        foto=foto,
        foto_alt=foto_alt,
        horario_tabla=horario.tabla,
        horario_estado=horario.estado,
        horario_js=horario.horario_js,
        ahora=horario.ahora,
    )

    @app.context_processor
    def _ctx():
        lang = lang_actual()
        return {
            "lang": lang,
            "otro": other_lang(lang),
            "estado": horario.estado(lang),
            "SITE_URL": app.config["SITE_URL"],
            "GA_ID": app.config["GA_MEASUREMENT_ID"],
        }


def _redirecciones(app: Flask) -> None:
    @app.before_request
    def _legacy():
        destino = LEGACY_REDIRECTS.get(request.path.rstrip("/") or "/")
        if destino:
            return redirect(destino, code=301)
        if request.path == "/en":
            return redirect("/en/", code=301)
        # Quitar la barra final (salvo la raíz y /en/) para tener una sola URL por página
        if request.path not in ("/", "/en/") and request.path.endswith("/") and not request.path.startswith("/static"):
            return redirect(request.path.rstrip("/"), code=301)
        return None


def _errores(app: Flask) -> None:
    @app.errorhandler(404)
    def _404(_e):
        g.lang = lang_actual()
        return render_template("errores/404.html", page=None, meta={
            "title": "Página no encontrada · Gosaria" if g.lang == "es" else "Page not found · Gosaria",
            "description": "", "noindex": True}), 404

    @app.errorhandler(500)
    def _500(_e):
        g.lang = lang_actual()
        return render_template("errores/500.html", page=None, meta={
            "title": "Error · Gosaria", "description": "", "noindex": True}), 500

    @app.errorhandler(400)
    def _400(_e):
        g.lang = lang_actual()
        return render_template("errores/400.html", page=None, meta={
            "title": "Error · Gosaria", "description": "", "noindex": True}), 400
