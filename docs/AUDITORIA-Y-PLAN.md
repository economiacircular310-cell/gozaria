# Gosaria · Auditoría del código y plan por fases

Revisión del código de `gosaria-web-servidor.zip` (Flask + SQLite + Jinja) hecha el 7 de octubre de 2026. Cada punto de la auditoría se ha comprobado leyendo el código y renderizando las páginas con la configuración de la demo (`deploy/env.demo`).

> **Estado:** pendiente de aprobación. Este documento no cambia nada en la web.

---

## 1. Qué se ha recibido

| Elemento | Estado |
|---|---|
| App Flask (`app.py`, `gosaria/`), plantillas, CSS/JS, fotos, `deploy/` | Recibido e importado al repositorio tal cual |
| `tests/` (el README habla de 45 pruebas) | **No viene en el ZIP** |
| `scripts/` y `assets_src/` (generar fotos AVIF/WebP y tipografía) | **No vienen en el ZIP** |
| `DESPLIEGUE.md` adjunto | **Es de otro proyecto** (Casa Chute: `cafechute`, Caddy, precios en COP). La guía de esta web es `deploy/LEEME-DESPLIEGUE.md` (Nginx + certbot, `/srv/gosaria-web`, puerto 8001) |

## 2. Lo que funciona y se conserva (verificado)

| Punto | Dónde | Resultado |
|---|---|---|
| Renderizado en servidor y rápido | Flask + Jinja, CSS en línea, JS propio de 10 KB | ✅ |
| Imágenes con hash de versión | `static_v()` añade `?v=<sha256>`; AVIF + WebP en 6 tamaños con `srcset` | ✅ (son AVIF **y** WebP, no solo WebP) |
| ES/EN con rutas traducidas | `gosaria/i18n.py` → `PAGES` (`/en/menu`, `/en/events-space`, `/en/the-space`, `/en/contact`) | ✅ |
| «Abierto ahora · hasta las X» | `gosaria/horario.py` (servidor) y `static/js/site.js` (cada minuto, hora de Madrid) | ✅ |
| Mapa de Google solo con consentimiento | Macro `mapa()`: el iframe se crea al pulsar «Cargar el mapa» | ✅ |
| Honeypot, CSRF, tiempo mínimo y límite por IP | `gosaria/security.py` | ✅ |
| «Saltar al contenido» y textos alternativos | `base.html`, `contenido.py` → `FOTOS_ALT` | ✅ |
| Mesas sin reserva | FAQ: «No. Funcionamos por orden de llegada, también con grupos» y `acceptsReservations: false` | ✅ Se mantiene |

## 3. Auditoría punto por punto

| # | Punto | Veredicto | Evidencia |
|---|---|---|---|
| 1 | La sala se gestiona por correo | **Confirmado** | `forms.sala()` solo valida y `_procesar()` guarda en `mensajes` y envía un correo. No hay disponibilidad, precio, confirmación ni pago |
| 2 | Formularios renderizados dos veces | **No es un bug de plantilla: es una variante sin JS / con JS**, pero sobra | `sala.html:105-106` y `contacto.html:29-30`: el formulario va una vez en `<noscript>` y otra en `<template>`. `site.js` lo monta al acercarse (para que el autorrelleno no trabaje durante la carga). Solo se ve uno, pero el HTML lleva el formulario dos veces |
| 3 | «Escribir una reseña» con `href` vacío | **Confirmado. Causa encontrada** | `config.env()` (`config.py:31`) devuelve `""` cuando la variable existe pero está vacía, y entonces no usa el valor por defecto. `deploy/env.demo` trae `NEGOCIO_GOOGLE_RESENA=` → `href=""` en `/`, `/en/` y `/enlaces`. El mismo fallo afecta a otras variables: `SMTP_PORT=` vacío hace que la app no arranque |
| 4 | Alérgenos solo en barra | **Confirmado** | La base de datos no tiene campo de alérgenos. `carta.html:49` solo dice «pídela al personal». El único filtro es «Solo vegetarianos» |
| 5 | «Sin gluten del día» y «dulce del día» | **Confirmado** | No hay ningún campo para esto. Solo existe la barra de aviso genérica (`/admin/aviso`) |
| 6 | Catering «para llevar» no se puede pedir | **Confirmado** | Solo hay la casilla «¿Quieres catering?» dentro del presupuesto de la sala |
| 7 | Talleres sin agenda ni venta de plazas | **Parcial** | La agenda existe (tabla `eventos` y su gestión en `/admin/agenda`), pero está vacía y solo admite un enlace externo. No hay aforo, plazas ni pago |
| 8 | Carta y catering incoherentes | **Confirmado. Hay más de un caso** | Cada plato pertenece a una sola sección (`db.py:19`), así que el mismo producto se escribe dos veces. Croquetas: carta con 8 uds, 4 sabores y 9 € (`seed.json:63`); catering con 15 uds, 5 sabores con setas y 15 € (`seed.json:104`). «Fingers de pollo» también está duplicado con textos distintos (`seed.json:62` y `:109`) |
| 9 | Sin teléfono ni WhatsApp | **Confirmado. El código ya lo soporta** | `NEGOCIO_TELEFONO` y `NEGOCIO_WHATSAPP` vacíos. Al rellenarlos aparecen en el pie, en la página de contacto y en la barra móvil. **Falta tu decisión** |
| 10 | Entorno de staging en `noindex, nofollow` | **Confirmado** | `NOINDEX_SITIO=1` en `env.demo` pone la meta `robots`, la cabecera `X-Robots-Tag` y un `robots.txt` sin sitemap. **No se toca sin tu permiso** |
| 11 | Datos estructurados | **Incompletos** | `CafeOrCoffeeShop` está en todas las páginas y `Menu` en la carta. **No hay `EventVenue`**. `Event` solo sale si hay eventos (hoy ninguno), con fechas sin zona horaria (`seo.py:120`), y le faltan `offers` e `image`. `servesCuisine` sale en español también en inglés. `Menu` no marca dietas sin gluten ni alérgenos, y omite la cafetería porque no tiene platos con precio |
| 12 | Euskera | **No preparado** | `LANGS = ("es", "en")` y `other_lang()` solo sabe alternar entre dos idiomas. Las columnas de la base son `_es`/`_en`. En las plantillas hay unos 110 textos escritos con `'…' if es else '…'` que habría que pasar al catálogo de textos |

### Otros hallazgos

- La hora del panel usa `datetime.now()` (`admin.py:90` y `:240`), que es la hora del servidor (UTC en el VPS), mientras que la web pública usa la hora de Madrid. Por eso los contadores de eventos «próximos» del panel se desfasan 1 o 2 horas.
- En el panel, escribir texto en el campo «orden» de un plato o una categoría produce un error 500 (`admin.py:138` y `:205`).
- El límite de envíos se guarda en memoria y por proceso. Con 2 *workers*, el límite real es el doble. Basta para formularios, pero no para reservas ni pagos.
- Cafés, tés y repostería no tienen precio en la carta (lo apunta el propio README como pendiente del cliente).

## 4. Plan por fases (propuesta)

Mantengo el stack actual (Flask + SQLite + Jinja, sin JavaScript de terceros): es rápido, ya está desplegado y aguanta sin problema el volumen de una cafetería. Las reservas y los pagos usarán transacciones de SQLite (`BEGIN IMMEDIATE`) para impedir que dos personas reserven la misma franja a la vez.

| Fase | Contenido | Puntos | Depende de ti |
|---|---|---|---|
| **0. Arreglos y base** | <ul><li>`env()`: una variable vacía usa el valor por defecto (arregla el `href` de la reseña)</li><li>Formulario una sola vez en el HTML</li><li>Hora de Madrid también en el panel</li><li>Validación del campo «orden»</li><li>`servesCuisine` en el idioma de la página</li><li>Fechas de `Event` con zona horaria</li><li>Suite de pruebas `pytest` (o recuperar la original)</li></ul> | 2, 3, parte de 11 | Enlace o Place ID de reseñas |
| **1. Catálogo único** | <ul><li>Tabla de **productos** única, con **formatos por canal**: carta, catering, tienda y regalo. Un mismo producto puede tener una ración de carta de 8 uds y una bandeja de catering de 15 uds</li><li>**14 alérgenos UE**, dietas (vegetariano, vegano, sin gluten) y filtro «sin…» en la carta</li><li>Pantalla del panel **«Hoy en vitrina»**, pensada para el móvil: marcar en segundos el sin gluten y el dulce del día; la portada y la carta lo muestran</li><li>Migración automática de los datos actuales</li></ul> | 4, 5, 8 | Tabla de alérgenos de cada plato (no se puede inventar: Reglamento UE 1169/2011). Resolver lo de las croquetas |
| **2. Reserva de la sala** | <ul><li>Calendario de disponibilidad por horas</li><li>Precio calculado al momento según las tarifas (25/30/35/50 €/h) y el catering</li><li>Prerreserva con bloqueo temporal, pago online (señal o total) y confirmación con archivo `.ics`</li><li>Panel con calendario para bloquear días, confirmar o cancelar</li><li>Correos de aviso</li></ul> | 1 | Pasarela de pago, señal o pago total, política de cancelación, aforo |
| **3. Talleres y exposiciones** | <ul><li>Agenda con aforo, precio y venta de plazas, lista de asistentes y lista de espera</li><li>Página de cada evento</li><li>`Event` completo con `offers`, `image` y `EventVenue`</li></ul> | 7, 11 | — |
| **4. Catering para llevar y regalos** | <ul><li>Pedido desde el catálogo con antelación mínima</li><li>Franja de recogida en el local</li><li>Pago online</li><li>Productos de la tienda y de regalo (lotes y, si queréis, tarjetas regalo)</li></ul> | 6 | Antelación mínima, zona o recogida, qué productos de regalo |
| **5. Euskera (preparado, sin publicar)** | <ul><li>Pasar los ~110 textos al catálogo</li><li>Idiomas configurables, traducciones en la base de datos y rutas `/eu/…`</li><li>Selector de 3 idiomas y `hreflang`</li><li>El euskera queda oculto hasta tener las traducciones revisadas</li></ul> | 12 | Traductor o revisión de los textos |
| **6. SEO y lanzamiento** | <ul><li>Revisión final de los datos estructurados</li><li>Cambio de DNS a `gosariapamplona.es` sin tocar MX ni TXT</li><li>Quitar el `noindex` **solo cuando lo autorices**</li></ul> | 10, 11 | Fecha de lanzamiento |

Las fases 2, 3 y 4 comparten la misma pasarela de pago y el mismo «carrito», que se construyen una sola vez en la fase 2.

## 5. Decisiones pendientes

1. **Resto del prompt:** llegó cortado en «3. Marca y enfoque → Arquitectura de marca».
2. **Teléfono y WhatsApp públicos:** ¿se añaden? ¿Con qué números? (punto 9)
3. **Enlace de reseñas de Google:** el enlace de «Pedir reseñas» del Perfil de Empresa o el Place ID.
4. **Pasarela de pago:**
   - **Stripe:** la recomiendo por rapidez de integración; admite tarjeta, Apple Pay y Google Pay.
   - **Redsys** (el TPV de vuestro banco): admite Bizum.

   En la sala, ¿señal (qué %) o pago completo? ¿Qué política de cancelación?
5. **Croquetas:**
   - ¿Son dos formatos legítimos (ración de 8 y bandeja de 15)?
   - ¿Las de setas existen también en carta?
6. **`tests/` y `scripts/`:** ¿los tenéis? Si no, en la fase 0 se escriben pruebas nuevas.
7. **`DESPLIEGUE.md`:** el que adjuntaste es de Casa Chute. ¿El staging de Gosaria está montado con `deploy/instalar.sh` de este proyecto?
