import subprocess
import json
from utils.logger import logger

def setup_webhook(webhook_url):
    """Configura o webhook no Railway"""
    try:
        # Verificar se o Railway CLI está instalado e logado
        result = subprocess.run(['railway', 'whoami'], 
                              capture_output=True, 
                              text=True)
        
        if result.returncode != 0:
            logger.error("Railway CLI não está configurado ou usuário não está logado")
            return False
        
        # Configurar webhook
        webhook_config = {
            "url": webhook_url,
            "events": ["deploy.success"]
        }
        
        # Salvar configuração em arquivo temporário
        with open('webhook_config.json', 'w') as f:
            json.dump(webhook_config, f)
        
        # Adicionar webhook usando Railway CLI
        result = subprocess.run(['railway', 'webhook', 'add', '-f', 'webhook_config.json'],
                              capture_output=True,
                              text=True)
        
        if result.returncode != 0:
            logger.error(f"Erro ao configurar webhook: {result.stderr}")
            return False
        
        logger.info("Webhook configurado com sucesso!")
        return True
    
    except Exception as e:
        logger.error(f"Erro ao configurar webhook: {str(e)}")
        return False

if __name__ == '__main__':
    # URL do seu webhook (ajuste conforme necessário)
    WEBHOOK_URL = "https://seu-dominio.com/webhook/railway"
    
    if setup_webhook(WEBHOOK_URL):
        print("✅ Webhook configurado com sucesso!")
    else:
        print("❌ Erro ao configurar webhook") 