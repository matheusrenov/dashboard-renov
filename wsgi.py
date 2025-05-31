"""
WSGI entry point for production deployment
"""

import os
from app import server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port) 