FROM python:3.9-slim

# Configurar variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATABASE_URL=/app/data/network_data.db

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar e definir diretório de trabalho
WORKDIR /app

# Criar diretório para dados e definir permissões
RUN mkdir -p /app/data && \
    chmod 777 /app/data && \
    touch /app/data/network_data.db && \
    chmod 666 /app/data/network_data.db

# Copiar requirements primeiro para aproveitar o cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Expor a porta
EXPOSE 8080

# Comando para executar a aplicação
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:server"] 