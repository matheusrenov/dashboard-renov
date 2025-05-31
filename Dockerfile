FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivos do projeto
COPY . .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Variáveis de ambiente
ENV PORT=8080
ENV FLASK_ENV=production
ENV WEBHOOK_PORT=5000
ENV PYTHONPATH=/app

# Expor portas
EXPOSE 8080
EXPOSE 5000

# Comando para iniciar
CMD ["gunicorn", "app:server", "-c", "gunicorn.conf.py"] 