"""Base de datos SQLite: carta, catering, tarifas, agenda, ajustes y mensajes.

El contenido inicial sale de data/seed.json la primera vez que se arranca.
Después se edita desde el panel /admin.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app, g

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY,
    seccion TEXT NOT NULL CHECK (seccion IN ('carta', 'catering', 'tarifas')),
    slug TEXT NOT NULL,
    nombre_es TEXT NOT NULL,
    nombre_en TEXT NOT NULL DEFAULT '',
    nota_es TEXT NOT NULL DEFAULT '',
    nota_en TEXT NOT NULL DEFAULT '',
    orden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS platos (
    id INTEGER PRIMARY KEY,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
    nombre_es TEXT NOT NULL,
    nombre_en TEXT NOT NULL DEFAULT '',
    desc_es TEXT NOT NULL DEFAULT '',
    desc_en TEXT NOT NULL DEFAULT '',
    precio_cent INTEGER,
    unidades_es TEXT NOT NULL DEFAULT '',
    unidades_en TEXT NOT NULL DEFAULT '',
    por_hora INTEGER NOT NULL DEFAULT 0,
    vegetariano INTEGER NOT NULL DEFAULT 0,
    destacado INTEGER NOT NULL DEFAULT 0,
    visible INTEGER NOT NULL DEFAULT 1,
    orden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY,
    titulo_es TEXT NOT NULL,
    titulo_en TEXT NOT NULL DEFAULT '',
    desc_es TEXT NOT NULL DEFAULT '',
    desc_en TEXT NOT NULL DEFAULT '',
    inicio TEXT NOT NULL,
    fin TEXT NOT NULL DEFAULT '',
    precio_es TEXT NOT NULL DEFAULT '',
    precio_en TEXT NOT NULL DEFAULT '',
    enlace TEXT NOT NULL DEFAULT '',
    visible INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS ajustes (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mensajes (
    id INTEGER PRIMARY KEY,
    tipo TEXT NOT NULL,
    creado TEXT NOT NULL,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL,
    telefono TEXT NOT NULL DEFAULT '',
    datos TEXT NOT NULL DEFAULT '{}',
    enviado_email INTEGER NOT NULL DEFAULT 0
);
"""

SEED_PATH = Path(__file__).resolve().parent / "data" / "seed.json"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app) -> None:
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(app.config["DATABASE"]) as con:
        con.executescript(SCHEMA)
        vacia = con.execute("SELECT COUNT(*) FROM categorias").fetchone()[0] == 0
        if vacia:
            seed(con)
    app.teardown_appcontext(close_db)


def seed(con: sqlite3.Connection) -> None:
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    for orden_cat, cat in enumerate(data["categorias"]):
        cur = con.execute(
            "INSERT INTO categorias (seccion, slug, nombre_es, nombre_en, nota_es, nota_en, orden)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cat["seccion"], cat["slug"], cat["nombre_es"], cat.get("nombre_en", ""),
             cat.get("nota_es", ""), cat.get("nota_en", ""), orden_cat),
        )
        for orden, p in enumerate(cat.get("platos", [])):
            con.execute(
                "INSERT INTO platos (categoria_id, nombre_es, nombre_en, desc_es, desc_en, precio_cent,"
                " unidades_es, unidades_en, por_hora, vegetariano, destacado, orden)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cur.lastrowid, p["nombre_es"], p.get("nombre_en", ""), p.get("desc_es", ""),
                 p.get("desc_en", ""), p.get("precio_cent"), p.get("unidades_es", ""),
                 p.get("unidades_en", ""), int(p.get("por_hora", 0)), int(p.get("vegetariano", 0)),
                 int(p.get("destacado", 0)), orden),
            )
    for clave, valor in data.get("ajustes", {}).items():
        con.execute("INSERT OR REPLACE INTO ajustes (clave, valor) VALUES (?, ?)", (clave, valor))
    for ev in data.get("eventos", []):
        con.execute(
            "INSERT INTO eventos (titulo_es, titulo_en, desc_es, desc_en, inicio, fin, precio_es, precio_en, enlace)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ev["titulo_es"], ev.get("titulo_en", ""), ev.get("desc_es", ""), ev.get("desc_en", ""),
             ev["inicio"], ev.get("fin", ""), ev.get("precio_es", ""), ev.get("precio_en", ""), ev.get("enlace", "")),
        )


# --- Lectura para la web pública -------------------------------------------

def _loc(row: sqlite3.Row, campo: str, lang: str) -> str:
    valor = row[f"{campo}_{lang}"] if f"{campo}_{lang}" in row.keys() else ""
    return valor or row[f"{campo}_es"]


def _plato(row: sqlite3.Row, lang: str) -> dict:
    return {
        "id": row["id"],
        "nombre": _loc(row, "nombre", lang),
        "desc": _loc(row, "desc", lang),
        "precio_cent": row["precio_cent"],
        "unidades": _loc(row, "unidades", lang),
        "por_hora": bool(row["por_hora"]),
        "vegetariano": bool(row["vegetariano"]),
        "destacado": bool(row["destacado"]),
    }


def secciones(seccion: str, lang: str) -> list[dict]:
    db = get_db()
    cats = db.execute(
        "SELECT * FROM categorias WHERE seccion = ? ORDER BY orden, id", (seccion,)
    ).fetchall()
    resultado = []
    for c in cats:
        platos = db.execute(
            "SELECT * FROM platos WHERE categoria_id = ? AND visible = 1 ORDER BY orden, id", (c["id"],)
        ).fetchall()
        resultado.append({
            "id": c["id"],
            "slug": c["slug"],
            "nombre": _loc(c, "nombre", lang),
            "nota": _loc(c, "nota", lang),
            "platos": [_plato(p, lang) for p in platos],
        })
    return [c for c in resultado if c["platos"] or c["nota"]]


def destacados(lang: str, limite: int = 4) -> list[dict]:
    rows = get_db().execute(
        "SELECT p.* FROM platos p JOIN categorias c ON c.id = p.categoria_id"
        " WHERE c.seccion = 'carta' AND p.visible = 1 AND p.destacado = 1"
        " ORDER BY c.orden, p.orden LIMIT ?", (limite,)
    ).fetchall()
    return [_plato(r, lang) for r in rows]


def precio_minimo_sala() -> int | None:
    row = get_db().execute(
        "SELECT MIN(p.precio_cent) FROM platos p JOIN categorias c ON c.id = p.categoria_id"
        " WHERE c.seccion = 'tarifas' AND p.visible = 1 AND p.precio_cent IS NOT NULL"
    ).fetchone()
    return row[0] if row else None


def eventos_proximos(lang: str, desde: datetime) -> list[dict]:
    rows = get_db().execute(
        "SELECT * FROM eventos WHERE visible = 1 AND COALESCE(NULLIF(fin, ''), inicio) >= ?"
        " ORDER BY inicio", (desde.strftime("%Y-%m-%dT%H:%M"),)
    ).fetchall()
    return [{
        "id": r["id"],
        "titulo": _loc(r, "titulo", lang),
        "desc": _loc(r, "desc", lang),
        "inicio": datetime.fromisoformat(r["inicio"]),
        "fin": datetime.fromisoformat(r["fin"]) if r["fin"] else None,
        "precio": _loc(r, "precio", lang),
        "enlace": r["enlace"],
    } for r in rows]


def ajustes() -> dict:
    return {r["clave"]: r["valor"] for r in get_db().execute("SELECT clave, valor FROM ajustes")}


def guardar_mensaje(tipo: str, nombre: str, email: str, telefono: str, datos: dict) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO mensajes (tipo, creado, nombre, email, telefono, datos) VALUES (?, ?, ?, ?, ?, ?)",
        (tipo, datetime.now().isoformat(timespec="seconds"), nombre, email, telefono,
         json.dumps(datos, ensure_ascii=False)),
    )
    db.commit()
    return cur.lastrowid


def marcar_enviado(mensaje_id: int) -> None:
    db = get_db()
    db.execute("UPDATE mensajes SET enviado_email = 1 WHERE id = ?", (mensaje_id,))
    db.commit()
