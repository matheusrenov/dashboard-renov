"""
WSGI entry point for production deployment
"""

from app import app

# Garantir que o servidor está disponível para o Gunicorn
application = app.server

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8080) 