import logging
import os
from datetime import datetime

# Criar diretório de logs se não existir
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

# Configurar logger
logger = logging.getLogger('railway_logs')
logger.setLevel(logging.INFO)

# Criar formatador
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Handler para arquivo
log_file = os.path.join(log_dir, f'railway_{datetime.now().strftime("%Y%m%d")}.log')
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Handler para console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def log_error(error, context=None):
    """Registra erros com contexto adicional"""
    error_msg = f"Erro: {str(error)}"
    if context:
        error_msg = f"{error_msg} | Contexto: {context}"
    logger.error(error_msg)
    
def log_info(message, context=None):
    """Registra informações com contexto adicional"""
    info_msg = message
    if context:
        info_msg = f"{info_msg} | Contexto: {context}"
    logger.info(info_msg)
    
def log_warning(message, context=None):
    """Registra avisos com contexto adicional"""
    warning_msg = message
    if context:
        warning_msg = f"{warning_msg} | Contexto: {context}"
    logger.warning(warning_msg)

def log_debug(message, context=None):
    """Registra mensagens de debug com contexto adicional"""
    debug_msg = message
    if context:
        debug_msg = f"{debug_msg} | Contexto: {context}"
    logger.debug(debug_msg) 