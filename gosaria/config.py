"""Configuración de la web y datos fijos del negocio.

Todo lo que puede cambiar entre entornos (claves, correo, teléfono, datos
fiscales) se lee de variables de entorno o de un archivo .env.
Ver .env.example para la lista completa.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Carga un .env sencillo (CLAVE=valor) sin dependencias externas."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


class Config:
    # --- Aplicación -------------------------------------------------------
    ENV = env("GOSARIA_ENV", "development")
    PRODUCTION = ENV == "production"
    SECRET_KEY = env("SECRET_KEY") or secrets.token_hex(32)
    SECRET_KEY_CONFIGURADA = bool(env("SECRET_KEY"))
    SITE_URL = env("SITE_URL", "https://gosariapamplona.es").rstrip("/")
    # Demo o pruebas en un subdominio: que Google no indexe nada
    NOINDEX_SITIO = env_bool("NOINDEX_SITIO")
    DATABASE = env("DATABASE_PATH", str(BASE_DIR / "instance" / "gosaria.sqlite3"))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = PRODUCTION
    SESSION_COOKIE_NAME = "gosaria_session"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 horas para el panel
    MAX_CONTENT_LENGTH = 64 * 1024  # los formularios no admiten archivos
    SEND_FILE_MAX_AGE_DEFAULT = 60 * 60 * 24 * 365  # estáticos versionados con ?v=
    COMPRESS_MIMETYPES = [
        "text/html", "text/css", "text/xml", "application/xml",
        "application/javascript", "text/javascript", "application/json",
        "application/manifest+json", "image/svg+xml", "text/plain",
    ]
    COMPRESS_MIN_SIZE = 500

    # --- Panel de administración ---------------------------------------
    # Contraseña en claro (solo desarrollo) o hash generado con:
    #   python -c "from werkzeug.security import generate_password_hash as g; print(g('tu-clave'))"
    ADMIN_PASSWORD = env("ADMIN_PASSWORD")
    ADMIN_PASSWORD_HASH = env("ADMIN_PASSWORD_HASH")

    # --- Correo (Microsoft 365 a través de GoDaddy) -------------------------
    SMTP_HOST = env("SMTP_HOST")  # p. ej. smtp.office365.com
    SMTP_PORT = int(env("SMTP_PORT", "587"))
    SMTP_USER = env("SMTP_USER")
    SMTP_PASSWORD = env("SMTP_PASSWORD")
    MAIL_FROM = env("MAIL_FROM", "contacto@gosariapamplona.es")
    MAIL_TO = env("MAIL_TO", "contacto@gosariapamplona.es")

    # --- Analítica (solo se carga si el visitante la acepta) -----------
    GA_MEASUREMENT_ID = env("GA_MEASUREMENT_ID")  # p. ej. G-XXXXXXXXXX


# Datos del negocio. Los que dependen del cliente se pueden sobrescribir con
# variables de entorno; si están vacíos, la web oculta el elemento (teléfono,
# WhatsApp, Glovo...) en lugar de mostrar un dato inventado.
NEGOCIO = {
    "nombre": "Gosaria",
    "nombre_largo": "Gosaria · Espacio de conexión",
    "email": env("NEGOCIO_EMAIL", "contacto@gosariapamplona.es"),
    "telefono": env("NEGOCIO_TELEFONO"),          # formato: +34 948 000 000
    "whatsapp": env("NEGOCIO_WHATSAPP"),          # solo dígitos con prefijo: 34600000000
    "direccion": {
        "calle": "Plaza Salesianos, 8",
        "cp": "31002",
        "ciudad": "Pamplona",
        "provincia": "Navarra",
        "pais": "ES",
    },
    "geo": {"lat": 42.8145276, "lng": -1.6363488},
    "rango_precio": "10–20 €",
    # Lunes = 0 ... Domingo = 6. Franjas en hora local de Pamplona.
    "horario": {
        0: [("09:00", "21:00")],
        1: [("09:00", "21:00")],
        2: [("09:00", "21:00")],
        3: [("09:00", "21:00")],
        4: [("09:00", "23:00")],
        5: [("09:00", "23:00")],
        6: [("09:00", "15:00")],
    },
    # Días de cierre excepcional (AAAA-MM-DD), p. ej. festivos.
    "cierres": [d for d in env("NEGOCIO_CIERRES").split(",") if d.strip()],
    "instagram": "https://www.instagram.com/gosariapamplona/",
    "instagram_usuario": "@gosariapamplona",
    "facebook": env("NEGOCIO_FACEBOOK"),
    "tiktok": env("NEGOCIO_TIKTOK"),
    "glovo": env("NEGOCIO_GLOVO"),
    "google_maps": "https://maps.google.com/?cid=15941943697503880790",
    "google_resenas": env("NEGOCIO_GOOGLE_RESENA", "https://maps.google.com/?cid=15941943697503880790"),
    "como_llegar": "https://www.google.com/maps/dir/?api=1&destination=GOSARIA+PAMPLONA%2C+Plaza+Salesianos+8%2C+31002+Pamplona",
    "mapa_embed": "https://www.google.com/maps?q=GOSARIA+PAMPLONA,+Plaza+Salesianos+8,+Pamplona&output=embed",
    "valoracion": {"nota": "4,3", "num": "299", "fecha": "octubre de 2026"},
    "sala_aforo": env("SALA_AFORO"),               # p. ej. "40 personas"
    "apertura": 2024,
}

# Datos del titular para el aviso legal. Mientras no se rellenen, las páginas
# legales muestran un aviso visible de "pendiente".
TITULAR = {
    "razon_social": env("TITULAR_RAZON_SOCIAL"),
    "nif": env("TITULAR_NIF"),
    "domicilio": env("TITULAR_DOMICILIO", "Plaza Salesianos, 8, 31002 Pamplona (Navarra)"),
    "email": env("TITULAR_EMAIL", "contacto@gosariapamplona.es"),
    "registro": env("TITULAR_REGISTRO"),  # datos registrales, si es sociedad
    "hosting": env("HOSTING_PROVEEDOR"),  # p. ej. "Render Services, Inc." para la política de privacidad
}
