from app import server, app
from flask import Flask, jsonify
from typing import cast
import os

# Garante que o servidor é uma instância Flask
flask_server = cast(Flask, server)

# Adiciona endpoint de healthcheck
@flask_server.route('/health')
def healthcheck():
    return jsonify({"status": "healthy"}), 200

# Configura a rota raiz para servir o Dash app
@flask_server.route('/')
def index():
    return app.index()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8081))
    flask_server.run(host='0.0.0.0', port=port) 