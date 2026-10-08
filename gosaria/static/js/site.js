/* Gosaria · interacción mínima (sin librerías). La web funciona sin JavaScript;
   esto solo añade el menú móvil, el estado en directo, las cookies, el mapa y filtros. */
(function () {
  "use strict";
  var doc = document;
  var root = doc.documentElement;
  var lang = root.lang || "es";

  function $(sel, ctx) { return (ctx || doc).querySelector(sel); }
  function $all(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }
  function leerJSON(id) {
    var el = doc.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  /* --- Menú móvil -------------------------------------------------------- */
  var toggle = $(".nav-toggle");
  var nav = $("#nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var abierto = nav.classList.toggle("abierto");
      toggle.setAttribute("aria-expanded", abierto ? "true" : "false");
    });
    doc.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("abierto")) {
        nav.classList.remove("abierto");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    });
  }

  /* --- Estado "abierto ahora" en directo (hora de Pamplona) --------------- */
  var horario = leerJSON("horario-data");
  function partesMadrid() {
    var f = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/Madrid", weekday: "short", year: "numeric", month: "2-digit",
      day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false
    }).formatToParts(new Date());
    var p = {};
    f.forEach(function (x) { p[x.type] = x.value; });
    var dias = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 };
    return { dia: dias[p.weekday], min: (+p.hour % 24) * 60 + (+p.minute), fecha: p.year + "-" + p.month + "-" + p.day };
  }
  function aMin(hm) { var s = hm.split(":"); return (+s[0]) * 60 + (+s[1]); }
  function hora(hm) { var s = hm.split(":"); return (+s[0]) + ":" + s[1]; }
  function fmt(plantilla, valores) {
    return plantilla.replace(/\{(\w)\}/g, function (_, k) { return valores[k]; });
  }
  function calcularEstado() {
    if (!horario) return null;
    var tx = horario.textos;
    var ahora = partesMadrid();
    var cerradoHoy = horario.cierres.indexOf(ahora.fecha) !== -1;
    var hoy = cerradoHoy ? [] : (horario.dias[String(ahora.dia)] || []);
    var i, franja;
    for (i = 0; i < hoy.length; i++) {
      franja = hoy[i];
      if (ahora.min >= aMin(franja[0]) && ahora.min < aMin(franja[1])) {
        return { abierto: true, texto: tx.abierto + " · " + fmt(tx.hasta, { h: hora(franja[1]) }) };
      }
    }
    for (i = 0; i < hoy.length; i++) {
      if (ahora.min < aMin(hoy[i][0])) {
        return { abierto: false, texto: tx.cerrado + " · " + fmt(tx.abre_hoy, { h: hora(hoy[i][0]) }) };
      }
    }
    for (var d = 1; d < 8; d++) {
      var dia = (ahora.dia + d) % 7;
      var fr = horario.dias[String(dia)] || [];
      if (fr.length) {
        var siguiente = d === 1 ? fmt(tx.abre_manana, { h: hora(fr[0][0]) }) : fmt(tx.abre_dia, { d: tx.dias[dia], h: hora(fr[0][0]) });
        return { abierto: false, texto: tx.cerrado + " · " + siguiente };
      }
    }
    return { abierto: false, texto: tx.cerrado };
  }
  function pintarEstado() {
    var e = calcularEstado();
    if (!e) return;
    $all("[data-estado]").forEach(function (el) {
      el.setAttribute("data-abierto", e.abierto ? "1" : "0");
      el.textContent = e.texto;
    });
  }
  if (horario) {
    // El servidor ya pinta el estado correcto; solo se recalcula al cambiar de minuto
    var restante = 60000 - (Date.now() % 60000) + 500;
    setTimeout(function () { pintarEstado(); setInterval(pintarEstado, 60000); }, restante);
  }

  /* --- Consentimiento de cookies y Google Analytics ---------------------- */
  var CLAVE = "gosaria_consent_v1";
  var gaId = root.getAttribute("data-ga") || "";
  var banner = $("#cookies");
  function leerConsentimiento() {
    try { return JSON.parse(localStorage.getItem(CLAVE) || "null"); } catch (e) { return null; }
  }
  function guardarConsentimiento(analitica) {
    var valor = { analitica: !!analitica, fecha: new Date().toISOString() };
    try { localStorage.setItem(CLAVE, JSON.stringify(valor)); } catch (e) { /* modo privado */ }
    return valor;
  }
  var gaCargado = false;
  function cargarGA() {
    if (!gaId || gaCargado) return;
    gaCargado = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("consent", "default", { ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied", analytics_storage: "granted" });
    window.gtag("js", new Date());
    window.gtag("config", gaId, { anonymize_ip: true });
    var s = doc.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(gaId);
    doc.head.appendChild(s);
  }
  function borrarCookiesGA() {
    doc.cookie.split(";").forEach(function (c) {
      var nombre = c.split("=")[0].trim();
      if (nombre.indexOf("_ga") === 0) {
        var dominio = location.hostname.replace(/^www\./, "");
        doc.cookie = nombre + "=; Max-Age=0; path=/";
        doc.cookie = nombre + "=; Max-Age=0; path=/; domain=." + dominio;
      }
    });
  }
  function aplicar(consent) {
    if (consent && consent.analitica) { cargarGA(); } else { borrarCookiesGA(); }
  }
  function abrirBanner(conOpciones) {
    if (!banner) return;
    banner.hidden = false;
    var opciones = $("#cookies-opciones", banner);
    var actual = leerConsentimiento();
    var casilla = $("#ck-analitica", banner);
    if (casilla) casilla.checked = !!(actual && actual.analitica);
    if (opciones) opciones.hidden = !conOpciones;
    var conf = $("[data-ck='configurar']", banner);
    if (conf) conf.hidden = !!conOpciones;
    var foco = $(conOpciones ? "#ck-analitica" : "[data-ck='aceptar']", banner);
    if (foco) foco.focus({ preventScroll: true });
  }
  function cerrarBanner() { if (banner) banner.hidden = true; }

  if (banner) {
    banner.addEventListener("click", function (e) {
      var accion = e.target.closest("[data-ck]");
      if (!accion) return;
      var tipo = accion.getAttribute("data-ck");
      if (tipo === "aceptar") { aplicar(guardarConsentimiento(true)); cerrarBanner(); }
      else if (tipo === "rechazar") { aplicar(guardarConsentimiento(false)); cerrarBanner(); }
      else if (tipo === "configurar") { $("#cookies-opciones", banner).hidden = false; accion.hidden = true; $("#ck-analitica", banner).focus(); }
      else if (tipo === "guardar") { aplicar(guardarConsentimiento($("#ck-analitica", banner).checked)); cerrarBanner(); }
    });
    var previo = leerConsentimiento();
    if (previo) { aplicar(previo); }
    else if (gaId) { abrirBanner(false); }
  }
  $all("[data-abrir-cookies]").forEach(function (b) {
    b.addEventListener("click", function () { abrirBanner(true); });
  });

  /* --- Mapa: solo se carga si el visitante lo pide ------------------------ */
  $all("[data-mapa]").forEach(function (caja) {
    var boton = $("button", caja);
    if (!boton) return;
    boton.addEventListener("click", function () {
      var iframe = doc.createElement("iframe");
      iframe.src = caja.getAttribute("data-mapa");
      iframe.title = caja.getAttribute("data-titulo") || "Mapa";
      iframe.loading = "lazy";
      iframe.referrerPolicy = "no-referrer-when-downgrade";
      iframe.setAttribute("allowfullscreen", "");
      caja.innerHTML = "";
      caja.appendChild(iframe);
    });
  });

  /* --- Carta: filtro de platos vegetarianos ------------------------------- */
  var filtro = $("#solo-veg");
  var carta = $("#carta");
  if (filtro && carta) {
    filtro.closest(".filtro").hidden = false;
    filtro.addEventListener("change", function () {
      carta.classList.toggle("solo-veg", filtro.checked);
      var aviso = $("#filtro-estado");
      if (aviso) {
        var n = $all(".plato[data-veg='1']", carta).length;
        aviso.textContent = filtro.checked ? (lang === "es" ? n + " platos vegetarianos" : n + " vegetarian dishes") : "";
      }
    });
  }

  /* --- Formularios: evitar doble envío y llevar el foco al error ---------- */
  $all("form[data-form]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var boton = $("button[type='submit']", form);
      if (boton) { boton.disabled = true; boton.setAttribute("aria-busy", "true"); }
    });
  });
  var resumen = $("[data-foco]");
  if (resumen) { resumen.focus(); }
})();
