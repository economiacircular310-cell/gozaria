"""Páginas públicas, redirecciones y archivos técnicos."""
import pytest

from gosaria.i18n import LANGS, PAGES


@pytest.mark.parametrize("ruta", [r for rutas in PAGES.values() for r in rutas.values()])
def test_todas_las_paginas_responden(client, ruta):
    resp = client.get(ruta)
    assert resp.status_code == 200
    assert "<title>" in resp.get_data(as_text=True)


@pytest.mark.parametrize("page", ["carta", "sala", "espacio", "contacto"])
def test_canonical_y_hreflang(client, page):
    html = client.get(PAGES[page]["es"]).get_data(as_text=True)
    assert f'<link rel="canonical" href="https://gosariapamplona.es{PAGES[page]["es"]}">' in html
    for lang in LANGS:
        assert f'hreflang="{lang}" href="https://gosariapamplona.es{PAGES[page][lang]}"' in html
    assert 'hreflang="x-default"' in html


def test_idioma_del_documento(client):
    assert '<html lang="es"' in client.get("/").get_data(as_text=True)
    assert '<html lang="en"' in client.get("/en/menu").get_data(as_text=True)


def test_404(client):
    resp = client.get("/no-existe")
    assert resp.status_code == 404
    assert 'content="noindex' in resp.get_data(as_text=True)


@pytest.mark.parametrize("origen, destino", [
    ("/inicio", "/"),
    ("/sala-multiusos", "/sala-y-eventos"),
    ("/carta/", "/carta"),
    ("/en", "/en/"),
])
def test_redirecciones_301(client, origen, destino):
    resp = client.get(origen)
    assert resp.status_code == 301
    assert resp.headers["Location"].endswith(destino)


def test_sitemap(client):
    xml = client.get("/sitemap.xml").get_data(as_text=True)
    assert "<loc>https://gosariapamplona.es/carta</loc>" in xml
    assert "<loc>https://gosariapamplona.es/en/menu</loc>" in xml
    assert "/enlaces" not in xml


def test_robots(client):
    texto = client.get("/robots.txt").get_data(as_text=True)
    assert "Disallow: /admin" in texto
    assert "Sitemap: https://gosariapamplona.es/sitemap.xml" in texto


def test_noindex_en_demo(app, client):
    app.config["NOINDEX_SITIO"] = True
    resp = client.get("/")
    assert resp.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert '<meta name="robots" content="noindex, nofollow">' in resp.get_data(as_text=True)
    assert "Sitemap:" not in client.get("/robots.txt").get_data(as_text=True)


def test_cabeceras_de_seguridad(client):
    resp = client.get("/")
    csp = resp.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp and "'nonce-" in csp
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_manifest_y_healthz(client):
    assert client.get("/manifest.webmanifest").get_json()["short_name"] == "Gosaria"
    assert client.get("/healthz").get_json()["ok"] is True


def test_mesas_sin_reserva(client):
    """La política se mantiene: las mesas de la cafetería no se reservan."""
    html = client.get("/").get_data(as_text=True)
    assert "orden de llegada" in html
