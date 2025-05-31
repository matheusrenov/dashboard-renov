import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from utils.logger import logger

def get_railway_logs(since=None):
    """Obtém logs do Railway usando o CLI"""
    try:
        # Verificar se o Railway CLI está instalado
        result = subprocess.run(['railway', 'logs'], 
                              capture_output=True, 
                              text=True)
        
        if result.returncode != 0:
            raise Exception(f"Erro ao obter logs: {result.stderr}")
        
        return result.stdout
    
    except Exception as e:
        logger.error(f"Erro ao obter logs do Railway: {str(e)}")
        return None

def save_logs(logs, output_dir='logs'):
    """Salva os logs em um arquivo"""
    try:
        # Criar diretório se não existir
        os.makedirs(output_dir, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'railway_logs_{timestamp}.txt'
        filepath = os.path.join(output_dir, filename)
        
        # Salvar logs
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(logs)
        
        logger.info(f"Logs salvos em: {filepath}")
        return filepath
    
    except Exception as e:
        logger.error(f"Erro ao salvar logs: {str(e)}")
        return None

def get_last_deploy_info():
    """Obtém informações do último deploy"""
    try:
        result = subprocess.run(['railway', 'status'], 
                              capture_output=True, 
                              text=True)
        
        if result.returncode != 0:
            raise Exception(f"Erro ao obter status: {result.stderr}")
        
        # Parsear saída para encontrar ID do deploy
        # Nota: Formato pode variar dependendo da versão do Railway CLI
        output = result.stdout
        if 'Deploy ID:' in output:
            deploy_id = output.split('Deploy ID:')[1].split('\n')[0].strip()
            return deploy_id
        
        return None
    
    except Exception as e:
        logger.error(f"Erro ao obter informações do deploy: {str(e)}")
        return None

def main(since=None, deploy_id=None):
    """Função principal"""
    logger.info("Iniciando sincronização de logs do Railway...")
    
    # Obter logs
    logs = get_railway_logs(since)
    if not logs:
        logger.error("Não foi possível obter os logs do Railway.")
        sys.exit(1)
    
    # Salvar logs
    log_file = save_logs(logs, deploy_id=deploy_id)
    if not log_file:
        logger.error("Não foi possível salvar os logs.")
        sys.exit(1)
    
    logger.info("Sincronização concluída com sucesso!")

if __name__ == '__main__':
    # Verificar argumentos
    since = None
    if len(sys.argv) > 1:
        since = sys.argv[1]
    
    # Obter ID do último deploy
    deploy_id = get_last_deploy_info()
    
    main(since, deploy_id) 