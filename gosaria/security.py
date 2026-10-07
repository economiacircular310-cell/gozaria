"""Seguridad: cabeceras HTTP, CSP con nonce, CSRF, antispam y límite de envíos."""
from __future__ import annotations

import hmac
import secrets
import time
from collections import defaultdict, deque

from flask import Flask, abort, current_app, g, request, session
from itsdangerous import BadSignature, URLSafeTimedSerializer


# --- Nonce para <style> y <script> en línea -------------------------------

def nonce() -> str:
    if "csp_nonce" not in g:
        g.csp_nonce = secrets.token_urlsafe(16)
    return g.csp_nonce


def _csp(ga: bool, produccion: bool) -> str:
    n = nonce()
    script = ["'self'", f"'nonce-{n}'"]
    img = ["'self'", "data:"]
    connect = ["'self'"]
    if ga:
        script.append("https://www.googletagmanager.com")
        img += ["https://www.google-analytics.com", "https://www.googletagmanager.com"]
        connect += ["https://*.google-analytics.com", "https://*.analytics.google.com",
                    "https://*.googletagmanager.com"]
    partes = [
        "default-src 'self'",
        f"script-src {' '.join(script)}",
        f"style-src 'self' 'nonce-{n}'",
        f"img-src {' '.join(img)}",
        "font-src 'self'",
        f"connect-src {' '.join(connect)}",
        "frame-src https://www.google.com",
        "form-action 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "manifest-src 'self'",
    ]
    if produccion:
        partes.append("upgrade-insecure-requests")
    return "; ".join(partes)


def install_headers(app: Flask) -> None:
    @app.after_request
    def _headers(resp):
        cfg = current_app.config
        if resp.mimetype == "text/html":
            resp.headers["Content-Security-Policy"] = _csp(bool(cfg["GA_MEASUREMENT_ID"]), cfg["PRODUCTION"])
            resp.headers.setdefault("Cache-Control", "no-cache")
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resp.headers["X-Frame-Options"] = "DENY"
        if cfg["PRODUCTION"]:
            resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        if request.path.startswith("/admin"):
            resp.headers["Cache-Control"] = "no-store"
            resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        elif cfg["NOINDEX_SITIO"]:
            resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        return resp


# --- CSRF ---------------------------------------------------------------

def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def csrf_valido() -> bool:
    enviado = request.form.get("csrf", "")
    guardado = session.get("csrf", "")
    return bool(enviado and guardado) and hmac.compare_digest(enviado, guardado)


def exigir_csrf() -> None:
    if not csrf_valido():
        abort(400)


# --- Antispam: campo trampa + tiempo mínimo de rellenado -------------------

def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="form-timer")


def form_timer() -> str:
    return _serializer().dumps(int(time.time()))


def parece_spam(min_segundos: int = 3) -> bool:
    """True si un bot rellenó el campo trampa o envió demasiado rápido."""
    if request.form.get("web", "").strip():
        return True
    try:
        inicio = _serializer().loads(request.form.get("t", ""), max_age=60 * 60 * 6)
    except BadSignature:
        return True
    return time.time() - int(inicio) < min_segundos


# --- Límite de envíos por IP (en memoria) ---------------------------------

_intentos: dict[str, deque] = defaultdict(deque)


def _ip() -> str:
    # Detrás de un proxy, configurar ProxyFix en wsgi.py para que esto sea la IP real.
    return request.remote_addr or "?"


def limite_superado(clave: str, maximo: int, ventana_seg: int) -> bool:
    ahora = time.time()
    cola = _intentos[f"{clave}:{_ip()}"]
    while cola and ahora - cola[0] > ventana_seg:
        cola.popleft()
    if len(cola) >= maximo:
        return True
    cola.append(ahora)
    return False


def reiniciar_limites() -> None:
    _intentos.clear()
