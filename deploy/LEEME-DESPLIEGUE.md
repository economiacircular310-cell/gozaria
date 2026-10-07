# Publicar la demo de Gosaria en un subdominio (VPS con SSH)

Tiempo estimado: 15 minutos. Requisitos:

- Un VPS con **Ubuntu 22.04/24.04 o Debian 12**, acceso SSH y un usuario con `sudo`.
- Poder crear registros DNS en el dominio del subdominio.

La instalación deja la web en `/srv/gosaria-web` y la pone en marcha con:

- **Gunicorn** como servicio de systemd (`gosaria`);
- **Nginx** delante;
- certificado **HTTPS de Let's Encrypt**, que se renueva solo.

Viene en **modo demo**: ninguna página se indexa en Google, para que no compita con la web actual del cliente.

---

## 1. Crear el subdominio en el DNS

En el panel DNS del dominio, crea un registro:

| Tipo | Nombre | Valor | TTL |
|---|---|---|---|
| A | `demo` (o el nombre que quieras) | IP de tu VPS | 600 |

- Si el subdominio es del dominio del cliente (`demo.gosariapamplona.es`), el DNS está en **GoDaddy**. Añade solo ese registro A y **no toques los MX ni los TXT**, porque el correo del cliente depende de ellos.
- Si usas un dominio tuyo (por ejemplo `gosaria.tuestudio.com`), créalo en tu proveedor.

Comprueba que ya apunta al VPS (puede tardar de 5 minutos a 1 hora):

```bash
nslookup demo.gosariapamplona.es
```

## 2. Subir el ZIP al servidor

Desde Windows (PowerShell), en la carpeta donde esté el ZIP:

```powershell
scp gosaria-web-servidor.zip usuario@IP_DEL_VPS:~
```

También puedes subirlo con WinSCP o FileZilla (por SFTP) a tu carpeta de usuario.

## 3. Instalar

```bash
ssh usuario@IP_DEL_VPS
sudo apt-get install -y unzip
unzip gosaria-web-servidor.zip
cd gosaria-web
sudo bash deploy/instalar.sh demo.gosariapamplona.es tu@correo.com
```

El script:

1. Comprueba que el DNS apunta al servidor.
2. Instala Python, Nginx y Certbot.
3. Copia la web, crea el entorno de Python y genera el `.env` con una clave secreta aleatoria. Te pedirá la **contraseña del panel /admin**, que se guarda cifrada.
4. Crea el servicio, configura Nginx y abre los puertos si usas `ufw`.
5. Pide el certificado HTTPS y redirige HTTP a HTTPS.

El correo que indicas solo lo usa Let's Encrypt para avisos del certificado. Al ejecutar el script aceptas sus condiciones de uso.

Al terminar verás:

```
Listo. Web: https://demo.gosariapamplona.es   Panel: https://demo.gosariapamplona.es/admin
```

## 4. Comprobar

- `https://demo.../` muestra la web, y `https://demo.../en/` la versión en inglés.
- `https://demo.../admin` pide la contraseña que elegiste.
- `https://demo.../healthz` devuelve `{"ok": true, ...}`.
- Para confirmar que la demo no se indexa: `curl -I https://demo.../` debe mostrar `X-Robots-Tag: noindex, nofollow`.

## 5. Demo con contraseña (opcional)

Si quieres que solo el cliente pueda verla:

```bash
sudo apt-get install -y apache2-utils
sudo htpasswd -c /etc/nginx/gosaria.htpasswd cliente
sudo nano /etc/nginx/sites-available/gosaria     # quita el # de las líneas auth_basic (en los dos bloques server si certbot creó el de HTTPS)
sudo nginx -t && sudo systemctl reload nginx
```

## 6. Actualizar a una versión nueva

Sube el ZIP nuevo y ejecuta:

```bash
rm -rf gosaria-web && unzip gosaria-web-servidor.zip && cd gosaria-web
sudo bash deploy/actualizar.sh
```

La base de datos (carta editada, mensajes) y el `.env` se conservan. Antes de actualizar se guarda una copia en `/var/backups/gosaria/`.

## 7. Comandos útiles

| Para | Comando |
|---|---|
| Ver si la web está en marcha | `sudo systemctl status gosaria` |
| Ver errores recientes | `sudo journalctl -u gosaria -n 100` |
| Reiniciar tras editar el `.env` | `sudo systemctl restart gosaria` |
| Editar la configuración | `sudo nano /srv/gosaria-web/.env` |
| Copia de la base de datos | `sudo cp /srv/gosaria-web/instance/gosaria.sqlite3 ~/` |
| Comprobar la renovación del HTTPS | `sudo certbot renew --dry-run` |

## 8. Cuando pase de demo a web definitiva

En `/srv/gosaria-web/.env`:

1. `SITE_URL=https://gosariapamplona.es` y `NOINDEX_SITIO=0`.
2. Rellena `SMTP_*`, para recibir los formularios por correo, y los datos del titular (`TITULAR_*`, `HOSTING_PROVEEDOR`).
3. Añade el dominio principal a Nginx y al certificado: `sudo certbot --nginx -d gosariapamplona.es -d www.gosariapamplona.es`.
4. En GoDaddy, apunta los registros A de `@` y `www` al VPS, **sin tocar MX ni TXT**.
5. Reinicia con `sudo systemctl restart gosaria`.
