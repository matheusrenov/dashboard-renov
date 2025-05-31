#!/bin/bash

# Diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Ativar ambiente virtual se existir
if [ -d "$PROJECT_DIR/venv" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# Executar script de sincronização
echo "Iniciando sincronização automática..."
python "$PROJECT_DIR/scripts/sync_railway_logs.py"

# Verificar status
if [ $? -eq 0 ]; then
    echo "Sincronização concluída com sucesso!"
else
    echo "Erro durante a sincronização!"
fi 