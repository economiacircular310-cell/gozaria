# Web de Gosaria Pamplona

Web nueva para **Gosaria** (cafetería de especialidad, Plaza Salesianos 8, Pamplona), hecha en **Python + Flask**, a partir de la auditoría de octubre de 2026.

- Español e inglés, con URLs propias para cada idioma.
- Carta, catering y tarifas de la sala en HTML (no en PDF), editables desde un panel.
- Formularios de contacto y de presupuesto de la sala, con protección antispam y cumplimiento del RGPD.
- Textos legales (aviso legal, privacidad, cookies) y banner de cookies con opción de rechazar.
- **Lighthouse: 100 / 100 / 100 / 100** (rendimiento, accesibilidad, buenas prácticas, SEO) en las 18 páginas, en móvil y escritorio.

---

## 1. Puesta en marcha (desarrollo)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # y rellena al menos SECRET_KEY y ADMIN_PASSWORD
python app.py                     # http://127.0.0.1:5000
```

En desarrollo puedes poner `GOSARIA_ENV=development` y `ADMIN_PASSWORD=algo` en `.env` para entrar al panel en `/admin`.

> **Windows y rutas largas:** si el proyecto está dentro de una carpeta con una ruta muy larga, `venv` puede fallar. En ese caso crea el entorno en una ruta corta (por ejemplo `C:\venvs\gosaria`).

Pruebas automáticas (páginas, redirecciones, formularios, seguridad, panel, horario y datos estructurados):

```bash
python -m pytest -q
```

## 2. Qué resuelve de la auditoría

| Problema detectado | Solución en la web nueva |
|---|---|
| Política de privacidad vacía, términos de plantilla, sin aviso legal | Aviso legal (LSSI art. 10), privacidad (RGPD) y cookies, en ES y EN. Los datos del titular que faltan se marcan en amarillo como **pendientes** |
| Banner solo con «Aceptar» y cookies de analítica antes de aceptar | Sin analítica por defecto. Si se activa GA4, solo se carga tras aceptar; «Rechazar» y «Aceptar» tienen el mismo peso; se puede reconfigurar desde el pie |
| Formulario sin información RGPD | Información básica de protección de datos y casilla obligatoria en los dos formularios |
| Carta en PDF-imagen, ilegible en el móvil e invisible para Google | Carta en HTML con precios, filtro vegetariano, nota de alérgenos y datos estructurados `Menu` |
| No dice qué es Gosaria | Portada con «Café de especialidad y brunch todo el día», botones *Ver la carta* y *Cómo llegar*, y estado «Abierto ahora» en directo |
| Sala sin fotos, aforo, tarifas ni forma de reservar | Página de sala con fotos, tarifas (25–50 €/h), catering con precios y formulario de presupuesto |
| «Sin próximos eventos» | Agenda que solo aparece cuando hay eventos (se gestionan desde el panel) |
| Sin teléfono, WhatsApp ni Glovo | Se muestran en cuanto se rellenan en `.env`, incluida una barra fija en el móvil |
| Título «INICIO», sin datos estructurados, 13/16 imágenes sin alt | Títulos y descripciones por página, `CafeOrCoffeeShop`, `Menu`, `FAQPage`, `Event` y `BreadcrumbList`, alt en todas las fotos, sitemap con hreflang |
| Móvil: 54/100 en rendimiento, LCP de 7,6 s | 100/100, LCP de 1,2–1,8 s (simulación móvil de Lighthouse). Fotos AVIF/WebP responsive, tipografía propia de 28 KB, sin JavaScript de terceros |
| Logo como captura de pantalla | Logotipo redibujado en SVG (provisional hasta tener el original en vectorial) |
| Premio sin aprovechar | Barra destacada «Finalistas a Cafetería con más encanto» con enlace para votar (editable desde el panel) |
| Web y redes desconectadas | Bloque de Instagram, página `/enlaces` para la biografía (con UTM), enlaces a Facebook/TikTok cuando existan |
| URLs antiguas de GoDaddy | Redirecciones 301: `/inicio`, `/sala-multiusos`, `/política-de-privacidad`, `/términos-y-condiciones` |

## 3. Panel de gestión (`/admin`)

Desde el panel, el propio local puede:

- **Carta, Catering y Tarifas:** añadir, editar, ocultar o borrar platos y categorías, en español e inglés, con precio, unidades, «vegetariano» y «destacado en la portada».
- **Agenda:** crear talleres y eventos (aparecen en la portada y en la página de la sala hasta que terminan).
- **Aviso:** la barra de color de arriba (premios, vacaciones, cambios de horario).
- **Mensajes:** leer los mensajes de los formularios y borrarlos (RGPD: como máximo 12 meses).

Para producción, genera el hash de la contraseña y ponlo en `.env`:

```bash
python -c "from werkzeug.security import generate_password_hash as g; print(g('una-contraseña-larga'))"
```

## 4. Configuración (`.env`)

Todas las variables están documentadas en `.env.example`. Las importantes:

| Variable | Para qué |
|---|---|
| `SECRET_KEY` | Obligatoria en producción. `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD_HASH` | Acceso al panel |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | Recibir los formularios por correo (Microsoft 365: `smtp.office365.com`, puerto 587). Hay que tener **activado SMTP AUTH** en el buzón (en Microsoft 365 suele venir desactivado). Sin SMTP, los mensajes se guardan igualmente en el panel |
| `NEGOCIO_TELEFONO`, `NEGOCIO_WHATSAPP`, `NEGOCIO_GLOVO` | Si están vacíos, la web no muestra esos botones |
| `TITULAR_RAZON_SOCIAL`, `TITULAR_NIF`, `HOSTING_PROVEEDOR` | Completan el aviso legal y la privacidad |
| `GA_MEASUREMENT_ID` | Google Analytics 4 (opcional). Al rellenarlo aparece el banner de cookies |
| `NEGOCIO_CIERRES` | Días de cierre excepcional, para que «Abierto ahora» sea correcto |

El horario semanal está en `gosaria/config.py` (`NEGOCIO["horario"]`).

## 5. Publicación

La web necesita un servidor con Python (no vale el hosting de GoDaddy Website Builder). Opciones sencillas:

- **Render / Railway / Fly.io:** comando de arranque `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`. Añade un disco persistente para `instance/` (base de datos SQLite).
- **VPS (Linux):** gunicorn + Nginx + certificado de Let's Encrypt.
- **Windows Server:** `waitress-serve --port=8000 app:app` detrás de IIS o Nginx.

Al cambiar el dominio:

1. En los DNS de GoDaddy, **cambia solo los registros de la web** (A y/o CNAME de `@` y `www`).
2. **No toques los MX ni los TXT**: el correo funciona con Microsoft 365 y se cortaría.
3. Añade un registro DMARC: `_dmarc  TXT  "v=DMARC1; p=none; rua=mailto:contacto@gosariapamplona.es"`.
4. Da de alta la web en Google Search Console y envía `https://gosariapamplona.es/sitemap.xml`.
5. En la ficha de Google, añade el teléfono y comprueba el enlace a la web.
6. En Instagram, pon en la biografía `https://gosariapamplona.es/enlaces`.

Copia de seguridad: basta con guardar `instance/gosaria.sqlite3` y el archivo `.env`.

## 6. Pendiente del cliente

- [ ] Razón social, NIF y, si es sociedad, datos registrales (aviso legal y privacidad).
- [ ] Proveedor de alojamiento definitivo (privacidad).
- [ ] Teléfono y WhatsApp.
- [ ] Enlace de Glovo y enlace directo para escribir una reseña en Google.
- [ ] Precios de cafés, bebidas y repostería (hoy la carta los describe sin precio), y precio de los suplementos (por ejemplo, la leche sin lactosa).
- [ ] Información de alérgenos de cada plato.
- [ ] Aforo de la sala (`SALA_AFORO`).
- [ ] Logo original en vectorial (SVG, AI o PDF).
- [ ] Fotos en alta resolución (las actuales salen de su web de GoDaddy).
- [ ] Revisión de los textos legales por un profesional.

## 7. Mantenimiento técnico

> `scripts/` y `assets_src/` no venían en el ZIP de esta versión: hay que recuperarlos del proyecto original antes de regenerar fotos o tipografía.

- **Fotos nuevas:** copiarlas en `assets_src/fotos/`, añadirlas a `FOTOS` en `scripts/build_assets.py` y ejecutar `python scripts/build_assets.py` (genera AVIF y WebP en 6 tamaños, iconos e imagen para redes).
- **Tipografía:** `python scripts/build_font.py` (Instrument Sans, licencia OFL, recortada a los caracteres que usa la web).
- **Textos de la interfaz:** `gosaria/i18n.py`. **Preguntas frecuentes y puntos fuertes:** `gosaria/contenido.py`.

### Estructura

```
app.py                 punto de entrada (WSGI)
gosaria/
  __init__.py          fábrica de la app, plantillas, redirecciones, errores
  config.py            configuración y datos del negocio
  public.py            páginas públicas, formularios, sitemap, robots
  admin.py             panel de gestión
  db.py                SQLite (carta, eventos, ajustes, mensajes)
  security.py          CSP con nonce, CSRF, antispam, límites
  seo.py               datos estructurados Schema.org
  horario.py           horario y «abierto ahora»
  i18n.py              rutas y textos ES/EN
  data/seed.json       contenido inicial (carta y catering de los PDF de 2026)
  templates/  static/
scripts/               generación de imágenes, iconos y tipografía
tests/                 pruebas (pytest)
```

## 8. Resultados de Lighthouse (6 de octubre de 2026)

Medido con Lighthouse 12 en local (simulación de móvil 4G y escritorio). Las 18 URLs (9 en español y 9 en inglés) dan **100 en rendimiento, accesibilidad, buenas prácticas y SEO**, con CLS 0 y TBT 0 ms.

| Página | LCP móvil | LCP escritorio |
|---|---|---|
| Inicio | 1,7 s | 0,4 s |
| Carta | 1,4 s | 0,3 s |
| Sala y eventos | 1,8 s | 0,4 s |
| El espacio | 1,7 s | 0,4 s |
| Contacto | 1,2 s | 0,3 s |
| Legales y enlaces | 1,2 s | 0,3 s |

En producción conviene repetir la medición con PageSpeed Insights, porque el servidor y la red reales cambian los tiempos.
