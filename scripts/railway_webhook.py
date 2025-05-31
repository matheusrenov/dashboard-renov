from flask import Flask, request, jsonify
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from scripts.sync_railway_logs import get_railway_logs, save_logs
from utils.logger import logger

app = Flask(__name__)

@app.route('/webhook/railway', methods=['POST'])
def railway_webhook():
    """Webhook para receber notificações do Railway"""
    try:
        data = request.json
        logger.info(f"Webhook recebido: {data}")
        
        # Capturar logs
        logs = get_railway_logs()
        if logs:
            log_file = save_logs(logs)
            if log_file:
                logger.info(f"Logs salvos em: {log_file}")
                return jsonify({"status": "success", "message": "Logs capturados com sucesso"})
        
        return jsonify({"status": "error", "message": "Falha ao capturar logs"}), 500
    
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('WEBHOOK_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 