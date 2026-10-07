"""Panel de administración: carta, catering, tarifas, agenda, aviso y mensajes."""
from __future__ import annotations

import json
from datetime import datetime
from functools import wraps

from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash

from . import security
from .db import get_db

bp = Blueprint("admin", __name__, url_prefix="/admin")

SECCIONES = {"carta": "Carta", "catering": "Catering", "tarifas": "Tarifas de la sala"}
AJUSTES_AVISO = ["aviso_activo", "aviso_es", "aviso_en", "aviso_enlace", "aviso_enlace_es", "aviso_enlace_en"]


def _admin_configurado() -> bool:
    cfg = current_app.config
    if cfg["PRODUCTION"]:
        return bool(cfg["ADMIN_PASSWORD_HASH"])  # en producción solo se acepta el hash
    return bool(cfg["ADMIN_PASSWORD_HASH"] or cfg["ADMIN_PASSWORD"])


def _clave_correcta(clave: str) -> bool:
    cfg = current_app.config
    if cfg["ADMIN_PASSWORD_HASH"]:
        return check_password_hash(cfg["ADMIN_PASSWORD_HASH"], clave)
    if cfg["ADMIN_PASSWORD"] and not cfg["PRODUCTION"]:
        import hmac
        return hmac.compare_digest(clave, cfg["ADMIN_PASSWORD"])
    return False


def login_requerido(view):
    @wraps(view)
    def envoltura(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin.login", next=request.path))
        if request.method == "POST":
            security.exigir_csrf()
        return view(*args, **kwargs)
    return envoltura


@bp.context_processor
def _ctx():
    return {"SECCIONES": SECCIONES, "lang": "es"}


# --- Acceso --------------------------------------------------------------

@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if not _admin_configurado():
        error = "El panel está desactivado: define ADMIN_PASSWORD_HASH en el archivo .env."
    elif request.method == "POST":
        security.exigir_csrf()
        if security.limite_superado("admin-login", maximo=8, ventana_seg=900):
            error = "Demasiados intentos. Espera 15 minutos."
        elif _clave_correcta(request.form.get("clave", "")):
            session.clear()
            session["admin"] = True
            session.permanent = True
            destino = request.args.get("next", "")
            return redirect(destino if destino.startswith("/admin") else url_for("admin.inicio"))
        else:
            error = "Contraseña incorrecta."
    return render_template("admin/login.html", error=error), (401 if error and request.method == "POST" else 200)


@bp.route("/logout", methods=["POST"])
@login_requerido
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@bp.route("")
@login_requerido
def inicio():
    db = get_db()
    resumen = {
        "platos": db.execute("SELECT COUNT(*) FROM platos p JOIN categorias c ON c.id = p.categoria_id WHERE c.seccion = 'carta'").fetchone()[0],
        "eventos": db.execute("SELECT COUNT(*) FROM eventos WHERE COALESCE(NULLIF(fin, ''), inicio) >= ?",
                              (datetime.now().strftime("%Y-%m-%dT%H:%M"),)).fetchone()[0],
        "mensajes": db.execute("SELECT COUNT(*) FROM mensajes").fetchone()[0],
        "sin_correo": db.execute("SELECT COUNT(*) FROM mensajes WHERE enviado_email = 0").fetchone()[0],
    }
    return render_template("admin/inicio.html", resumen=resumen,
                           smtp=bool(current_app.config["SMTP_HOST"]))


# --- Carta, catering y tarifas -------------------------------------------

@bp.route("/carta")
@login_requerido
def carta():
    seccion = request.args.get("seccion", "carta")
    if seccion not in SECCIONES:
        abort(404)
    db = get_db()
    cats = db.execute("SELECT * FROM categorias WHERE seccion = ? ORDER BY orden, id", (seccion,)).fetchall()
    platos = {c["id"]: db.execute("SELECT * FROM platos WHERE categoria_id = ? ORDER BY orden, id",
                                  (c["id"],)).fetchall() for c in cats}
    return render_template("admin/carta.html", seccion=seccion, categorias=cats, platos=platos)


def _precio_a_cent(texto: str) -> int | None:
    texto = (texto or "").strip().replace("€", "").replace(",", ".")
    if not texto:
        return None
    return round(float(texto) * 100)


def _form_plato() -> tuple[dict, str | None]:
    f = request.form
    try:
        precio = _precio_a_cent(f.get("precio", ""))
    except ValueError:
        return {}, "El precio debe ser un número, por ejemplo 8,50."
    datos = {
        "nombre_es": f.get("nombre_es", "").strip(),
        "nombre_en": f.get("nombre_en", "").strip(),
        "desc_es": f.get("desc_es", "").strip(),
        "desc_en": f.get("desc_en", "").strip(),
        "precio_cent": precio,
        "unidades_es": f.get("unidades_es", "").strip(),
        "unidades_en": f.get("unidades_en", "").strip(),
        "por_hora": int(f.get("por_hora") == "1"),
        "vegetariano": int(f.get("vegetariano") == "1"),
        "destacado": int(f.get("destacado") == "1"),
        "visible": int(f.get("visible") == "1"),
        "orden": int(f.get("orden") or 0),
    }
    if not datos["nombre_es"]:
        return datos, "El nombre en español es obligatorio."
    return datos, None


@bp.route("/plato/nuevo", methods=["GET", "POST"])
@bp.route("/plato/<int:plato_id>", methods=["GET", "POST"])
@login_requerido
def plato(plato_id: int | None = None):
    db = get_db()
    actual = None
    if plato_id:
        actual = db.execute("SELECT * FROM platos WHERE id = ?", (plato_id,)).fetchone() or abort(404)
        categoria_id = actual["categoria_id"]
    else:
        categoria_id = int(request.values.get("categoria", 0))
    categoria = db.execute("SELECT * FROM categorias WHERE id = ?", (categoria_id,)).fetchone() or abort(404)
    error = None
    if request.method == "POST":
        datos, error = _form_plato()
        if not error:
            if actual:
                campos = ", ".join(f"{k} = ?" for k in datos)
                db.execute(f"UPDATE platos SET {campos} WHERE id = ?", (*datos.values(), plato_id))
            else:
                if not datos["orden"]:
                    datos["orden"] = db.execute("SELECT COALESCE(MAX(orden), 0) + 1 FROM platos WHERE categoria_id = ?",
                                                (categoria_id,)).fetchone()[0]
                cols = ", ".join(["categoria_id", *datos])
                marcas = ", ".join("?" * (len(datos) + 1))
                db.execute(f"INSERT INTO platos ({cols}) VALUES ({marcas})", (categoria_id, *datos.values()))
            db.commit()
            flash("Guardado.")
            return redirect(url_for("admin.carta", seccion=categoria["seccion"]) + f"#cat-{categoria_id}")
        actual = {**(dict(actual) if actual else {}), **datos}
    return render_template("admin/plato.html", plato=actual, categoria=categoria, error=error)


@bp.route("/plato/<int:plato_id>/borrar", methods=["POST"])
@login_requerido
def plato_borrar(plato_id: int):
    db = get_db()
    fila = db.execute("SELECT p.id, c.seccion FROM platos p JOIN categorias c ON c.id = p.categoria_id WHERE p.id = ?",
                      (plato_id,)).fetchone() or abort(404)
    db.execute("DELETE FROM platos WHERE id = ?", (plato_id,))
    db.commit()
    flash("Plato eliminado.")
    return redirect(url_for("admin.carta", seccion=fila["seccion"]))


@bp.route("/categoria/nueva", methods=["GET", "POST"])
@bp.route("/categoria/<int:cat_id>", methods=["GET", "POST"])
@login_requerido
def categoria(cat_id: int | None = None):
    db = get_db()
    actual = db.execute("SELECT * FROM categorias WHERE id = ?", (cat_id,)).fetchone() if cat_id else None
    if cat_id and not actual:
        abort(404)
    seccion = actual["seccion"] if actual else request.values.get("seccion", "carta")
    if seccion not in SECCIONES:
        abort(404)
    error = None
    if request.method == "POST":
        f = request.form
        datos = {k: f.get(k, "").strip() for k in ("nombre_es", "nombre_en", "nota_es", "nota_en")}
        datos["orden"] = int(f.get("orden") or 0)
        if not datos["nombre_es"]:
            error = "El nombre en español es obligatorio."
        else:
            if actual:
                db.execute("UPDATE categorias SET nombre_es=?, nombre_en=?, nota_es=?, nota_en=?, orden=? WHERE id=?",
                           (*datos.values(), cat_id))
            else:
                slug = "".join(ch if ch.isalnum() else "-" for ch in datos["nombre_es"].lower()).strip("-")
                db.execute("INSERT INTO categorias (seccion, slug, nombre_es, nombre_en, nota_es, nota_en, orden)"
                           " VALUES (?, ?, ?, ?, ?, ?, ?)", (seccion, slug, *datos.values()))
            db.commit()
            flash("Categoría guardada.")
            return redirect(url_for("admin.carta", seccion=seccion))
        actual = {**(dict(actual) if actual else {}), **datos}
    return render_template("admin/categoria.html", categoria=actual, seccion=seccion, error=error)


@bp.route("/categoria/<int:cat_id>/borrar", methods=["POST"])
@login_requerido
def categoria_borrar(cat_id: int):
    db = get_db()
    fila = db.execute("SELECT seccion FROM categorias WHERE id = ?", (cat_id,)).fetchone() or abort(404)
    db.execute("DELETE FROM categorias WHERE id = ?", (cat_id,))
    db.commit()
    flash("Categoría y sus platos eliminados.")
    return redirect(url_for("admin.carta", seccion=fila["seccion"]))


# --- Agenda --------------------------------------------------------------

@bp.route("/agenda")
@login_requerido
def agenda():
    eventos = get_db().execute("SELECT * FROM eventos ORDER BY inicio DESC").fetchall()
    return render_template("admin/agenda.html", eventos=eventos, ahora=datetime.now().strftime("%Y-%m-%dT%H:%M"))


@bp.route("/evento/nuevo", methods=["GET", "POST"])
@bp.route("/evento/<int:evento_id>", methods=["GET", "POST"])
@login_requerido
def evento(evento_id: int | None = None):
    db = get_db()
    actual = db.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone() if evento_id else None
    if evento_id and not actual:
        abort(404)
    error = None
    if request.method == "POST":
        f = request.form
        campos = ("titulo_es", "titulo_en", "desc_es", "desc_en", "inicio", "fin", "precio_es", "precio_en", "enlace")
        datos = {k: f.get(k, "").strip() for k in campos}
        datos["visible"] = int(f.get("visible") == "1")
        try:
            datetime.fromisoformat(datos["inicio"])
            if datos["fin"]:
                datetime.fromisoformat(datos["fin"])
        except ValueError:
            error = "Revisa la fecha y hora de inicio (y de fin, si la pones)."
        if not datos["titulo_es"]:
            error = "El título en español es obligatorio."
        if datos["enlace"] and not datos["enlace"].startswith(("https://", "http://")):
            error = "El enlace debe empezar por https://"
        if not error:
            if actual:
                sets = ", ".join(f"{k} = ?" for k in datos)
                db.execute(f"UPDATE eventos SET {sets} WHERE id = ?", (*datos.values(), evento_id))
            else:
                cols = ", ".join(datos)
                db.execute(f"INSERT INTO eventos ({cols}) VALUES ({', '.join('?' * len(datos))})", tuple(datos.values()))
            db.commit()
            flash("Evento guardado.")
            return redirect(url_for("admin.agenda"))
        actual = {**(dict(actual) if actual else {}), **datos}
    return render_template("admin/evento.html", evento=actual, error=error)


@bp.route("/evento/<int:evento_id>/borrar", methods=["POST"])
@login_requerido
def evento_borrar(evento_id: int):
    db = get_db()
    db.execute("DELETE FROM eventos WHERE id = ?", (evento_id,))
    db.commit()
    flash("Evento eliminado.")
    return redirect(url_for("admin.agenda"))


# --- Aviso destacado -----------------------------------------------------

@bp.route("/aviso", methods=["GET", "POST"])
@login_requerido
def aviso():
    db = get_db()
    if request.method == "POST":
        enlace = request.form.get("aviso_enlace", "").strip()
        if enlace and not enlace.startswith(("https://", "http://")):
            flash("El enlace debe empezar por https://. No se ha guardado.")
            return redirect(url_for("admin.aviso"))
        for clave in AJUSTES_AVISO:
            if clave == "aviso_activo":
                valor = "1" if request.form.get(clave) == "1" else "0"
            else:
                valor = request.form.get(clave, "").strip()
            db.execute("INSERT OR REPLACE INTO ajustes (clave, valor) VALUES (?, ?)", (clave, valor))
        db.commit()
        flash("Aviso guardado.")
        return redirect(url_for("admin.aviso"))
    ajustes = {r["clave"]: r["valor"] for r in db.execute("SELECT clave, valor FROM ajustes")}
    return render_template("admin/aviso.html", ajustes=ajustes)


# --- Mensajes ------------------------------------------------------------

@bp.route("/mensajes")
@login_requerido
def mensajes():
    filas = get_db().execute("SELECT * FROM mensajes ORDER BY creado DESC").fetchall()
    lista = [{**dict(r), "datos": json.loads(r["datos"] or "{}")} for r in filas]
    return render_template("admin/mensajes.html", mensajes=lista)


@bp.route("/mensaje/<int:mensaje_id>/borrar", methods=["POST"])
@login_requerido
def mensaje_borrar(mensaje_id: int):
    db = get_db()
    db.execute("DELETE FROM mensajes WHERE id = ?", (mensaje_id,))
    db.commit()
    flash("Mensaje eliminado.")
    return redirect(url_for("admin.mensajes"))
