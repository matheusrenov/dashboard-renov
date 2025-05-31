"""
WSGI entry point for production deployment
"""

from app import server

# Garantir que o servidor está disponível para o Gunicorn
application = server

if __name__ == "__main__":
    application.run() 