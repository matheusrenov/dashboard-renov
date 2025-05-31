import multiprocessing
import os

# Configurações básicas
bind = "0.0.0.0:8080"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
worker_class = "gthread"
worker_connections = 1000
timeout = 120
keepalive = 5

# Configurações de logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Configurações de performance
max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 120
preload_app = True

# Configurações de segurança
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Configurações de debug (desativado em produção)
reload = False
capture_output = True
enable_stdio_inheritance = True

# Configurações de SSL/TLS (se necessário)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Configurações de processo
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Hooks
def on_starting(server):
    """Log quando o servidor está iniciando"""
    server.log.info("Iniciando servidor Gunicorn...")

def on_reload(server):
    """Log quando o servidor está recarregando"""
    server.log.info("Recarregando servidor Gunicorn...")

def post_fork(server, worker):
    """Configurações após o fork do worker"""
    server.log.info(f"Worker {worker.pid} inicializado") 