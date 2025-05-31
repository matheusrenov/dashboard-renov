"""
WSGI entry point for production deployment
"""

import os
from app import server

# Garantir que o servidor está disponível para o Gunicorn
application = server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    application.run(host="0.0.0.0", port=port) 