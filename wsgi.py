from app import server, app, PORT, HOST
from flask import Flask, jsonify
from typing import cast
import os

"""
Arquivo WSGI para execução em produção

Este arquivo é usado pelo Gunicorn para servir a aplicação.
Por padrão, usa a porta 8080 ou a definida pela variável de ambiente PORT.

Execução via Gunicorn:
    gunicorn wsgi:server --bind 0.0.0.0:8080

Execução via Procfile:
    web: gunicorn wsgi:server --workers 4 --threads 2 --timeout 120
"""

# Garante que o servidor é uma instância Flask
flask_server = cast(Flask, server)

# Adiciona endpoint de healthcheck
@flask_server.route('/health')
def healthcheck():
    """Endpoint para verificação de saúde do servidor"""
    return jsonify({
        "status": "healthy",
        "port": PORT,
        "environment": os.environ.get('FLASK_ENV', 'production')
    }), 200

# Configura a rota raiz para servir o Dash app
@flask_server.route('/')
def index():
    return app.index()

if __name__ == "__main__":
    print(f"Iniciando servidor em http://{HOST}:{PORT}")
    print(f"Ambiente: production")
    print(f"Porta: {PORT}")
    server.run() 