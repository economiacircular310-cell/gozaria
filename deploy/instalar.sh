#!/usr/bin/env bash
# Instala la web de Gosaria en un VPS Ubuntu (22.04/24.04) o Debian (12)
# con Nginx + Gunicorn + HTTPS de Let's Encrypt.
#
# Uso, como root y desde la carpeta descomprimida:
#   sudo bash deploy/instalar.sh demo.tudominio.com tu@correo.com
#
# Antes: el subdominio debe tener un registro DNS de tipo A apuntando a la IP del VPS.
# Se puede volver a ejecutar sin perder la base de datos ni el .env.
set -euo pipefail

DOMINIO="${1:-}"
CORREO="${2:-}"
DESTINO=/srv/gosaria-web
USUARIO=gosaria
PUERTO=8001
ORIGEN="$(cd "$(dirname "$0")/.." && pwd)"

if [ -z "$DOMINIO" ] || [ -z "$CORREO" ]; then
  echo "Uso: sudo bash deploy/instalar.sh demo.tudominio.com tu@correo.com"
  exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
  echo "Ejecuta el script con sudo."
  exit 1
fi

paso() { printf '\n\033[1;35m==> %s\033[0m\n' "$1"; }

paso "Comprobando el DNS de $DOMINIO"
IP_DNS="$(getent ahostsv4 "$DOMINIO" | awk 'NR==1{print $1}' || true)"
IP_VPS="$(curl -fsS -4 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
echo "El DNS apunta a: ${IP_DNS:-(sin resolver)} · IP de este servidor: $IP_VPS"
if [ "$IP_DNS" != "$IP_VPS" ]; then
  echo "AVISO: el subdominio todavía no apunta a este servidor. El certificado HTTPS fallará"
  echo "hasta que el registro A esté propagado. Puedes seguir y repetir el script más tarde."
  read -r -p "¿Continuar de todos modos? [s/N] " RESP
  [[ "$RESP" =~ ^[sSyY]$ ]] || exit 1
fi

paso "Instalando paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx certbot python3-certbot-nginx rsync curl >/dev/null

paso "Copiando la web a $DESTINO"
id -u "$USUARIO" >/dev/null 2>&1 || useradd --system --home-dir "$DESTINO" --shell /usr/sbin/nologin "$USUARIO"
mkdir -p "$DESTINO/instance"
rsync -a --delete \
  --exclude '.env' --exclude 'instance/' --exclude '.venv/' --exclude 'deploy/' \
  --exclude '__pycache__/' --exclude '*.pyc' \
  "$ORIGEN"/ "$DESTINO"/

paso "Creando el entorno de Python"
[ -x "$DESTINO/.venv/bin/python" ] || python3 -m venv "$DESTINO/.venv"
"$DESTINO/.venv/bin/pip" install -q --upgrade pip
"$DESTINO/.venv/bin/pip" install -q -r "$DESTINO/requirements-servidor.txt"

paso "Configuración (.env)"
if [ -f "$DESTINO/.env" ]; then
  echo "Ya existe $DESTINO/.env: se conserva."
else
  if [ -z "${ADMIN_CLAVE:-}" ]; then
    while true; do
      read -r -s -p "Elige una contraseña para el panel /admin (mínimo 10 caracteres): " ADMIN_CLAVE; echo
      [ "${#ADMIN_CLAVE}" -ge 10 ] && break
      echo "Demasiado corta."
    done
  fi
  HASH="$("$DESTINO/.venv/bin/python" -c 'import sys; from werkzeug.security import generate_password_hash as g; print(g(sys.argv[1]))' "$ADMIN_CLAVE")"
  SECRETO="$("$DESTINO/.venv/bin/python" -c 'import secrets; print(secrets.token_hex(32))')"
  sed -e "s|^SECRET_KEY=.*|SECRET_KEY=$SECRETO|" \
      -e "s|^SITE_URL=.*|SITE_URL=https://$DOMINIO|" \
      -e "s|^ADMIN_PASSWORD_HASH=.*|ADMIN_PASSWORD_HASH=$HASH|" \
      "$ORIGEN/deploy/env.demo" > "$DESTINO/.env"
  unset ADMIN_CLAVE
  echo "Creado $DESTINO/.env (modo demo: NOINDEX_SITIO=1)."
fi
chown -R "$USUARIO:$USUARIO" "$DESTINO"
chmod 600 "$DESTINO/.env"
chmod 750 "$DESTINO/instance"

paso "Servicio de la web (Gunicorn + systemd)"
sed -e "s|__DESTINO__|$DESTINO|g" -e "s|__USUARIO__|$USUARIO|g" -e "s|__PUERTO__|$PUERTO|g" \
  "$ORIGEN/deploy/gosaria.service" > /etc/systemd/system/gosaria.service
systemctl daemon-reload
systemctl enable gosaria >/dev/null
systemctl restart gosaria
sleep 2
if ! curl -fsS -o /dev/null "http://127.0.0.1:$PUERTO/healthz"; then
  echo "La aplicación no responde. Revisa el registro con: journalctl -u gosaria -n 50"
  exit 1
fi
echo "La aplicación responde en 127.0.0.1:$PUERTO"

paso "Nginx"
sed -e "s|__DOMINIO__|$DOMINIO|g" -e "s|__DESTINO__|$DESTINO|g" -e "s|__PUERTO__|$PUERTO|g" \
  "$ORIGEN/deploy/nginx-gosaria.conf" > /etc/nginx/sites-available/gosaria
ln -sf /etc/nginx/sites-available/gosaria /etc/nginx/sites-enabled/gosaria
nginx -t
systemctl reload nginx
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 'Nginx Full' >/dev/null
fi

paso "Certificado HTTPS (Let's Encrypt)"
if certbot --nginx -d "$DOMINIO" -m "$CORREO" --agree-tos --no-eff-email --non-interactive --redirect; then
  sleep 1
  ESTADO="$(curl -fsS -o /dev/null -w '%{http_code}' "https://$DOMINIO/healthz" || true)"
  echo "Comprobación HTTPS: $ESTADO"
  printf '\n\033[1;32mListo.\033[0m Web: https://%s   Panel: https://%s/admin\n' "$DOMINIO" "$DOMINIO"
else
  echo "No se pudo obtener el certificado (¿el DNS ya apunta a este servidor?)."
  echo "La web funciona por HTTP en http://$DOMINIO, pero el panel /admin necesita HTTPS."
  echo "Cuando el DNS esté listo, ejecuta: sudo certbot --nginx -d $DOMINIO --redirect"
fi
