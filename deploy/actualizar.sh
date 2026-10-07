#!/usr/bin/env bash
# Actualiza la web con una versión nueva sin tocar la base de datos ni el .env.
# Uso, como root y desde la carpeta descomprimida de la versión nueva:
#   sudo bash deploy/actualizar.sh
set -euo pipefail

DESTINO=/srv/gosaria-web
USUARIO=gosaria
ORIGEN="$(cd "$(dirname "$0")/.." && pwd)"

[ "$(id -u)" -eq 0 ] || { echo "Ejecuta el script con sudo."; exit 1; }
[ -f "$DESTINO/.env" ] || { echo "No hay instalación en $DESTINO. Usa primero deploy/instalar.sh"; exit 1; }

echo "==> Copia de seguridad de la base de datos"
mkdir -p /var/backups/gosaria
if [ -f "$DESTINO/instance/gosaria.sqlite3" ]; then
  cp "$DESTINO/instance/gosaria.sqlite3" "/var/backups/gosaria/gosaria-$(date +%Y%m%d-%H%M%S).sqlite3"
fi

echo "==> Copiando archivos"
rsync -a --delete \
  --exclude '.env' --exclude 'instance/' --exclude '.venv/' --exclude 'deploy/' \
  --exclude '__pycache__/' --exclude '*.pyc' \
  "$ORIGEN"/ "$DESTINO"/
"$DESTINO/.venv/bin/pip" install -q -r "$DESTINO/requirements-servidor.txt"
chown -R "$USUARIO:$USUARIO" "$DESTINO"

echo "==> Reiniciando"
systemctl restart gosaria
sleep 2
curl -fsS -o /dev/null -w "La web responde: %{http_code}\n" "http://127.0.0.1:8001/healthz"
