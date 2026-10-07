"""Punto de entrada.

Desarrollo:   python app.py            -> http://127.0.0.1:5000
Producción:   waitress-serve --port=8000 app:app   (Windows)
              gunicorn -w 2 -b 0.0.0.0:8000 app:app  (Linux)
"""
from werkzeug.middleware.proxy_fix import ProxyFix

from gosaria import create_app

app = create_app()
# Detrás de un proxy (Render, Railway, Nginx...) para obtener la IP y el HTTPS reales
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

if __name__ == "__main__":
    app.run(debug=not app.config["PRODUCTION"], port=5000)
