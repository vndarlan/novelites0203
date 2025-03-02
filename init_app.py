import os
import sys
import logging
import json
from typing import Dict

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_directories():
    """Inicializa os diretórios necessários para o funcionamento do aplicativo"""
    directories = [
        "db",
        "utils",
        "static",
        "static/screenshots"
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Diretório criado: {directory}")

def init_database():
    """Inicializa o banco de dados"""
    try:
        # Importar após criar diretórios
        from db.database import init_db
        
        # Inicializar banco de dados
        init_db()
        logger.info("Banco de dados inicializado com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        return False

def init_default_config():
    """Inicializa configurações padrão no banco de dados"""
    try:
        from db.database import get_db_session
        from db.models import ApiKey
        
        default_browser_config = {
            'headless': True,
            'disable_security': True,
            'browser_window_width': 1280,
            'browser_window_height': 1100,
            'highlight_elements': True,
            'chrome_instance_path': None,
            'wait_for_network_idle': 3.0,
            'minimum_wait_page_load_time': 0.5,
            'maximum_wait_page_load_time': 5.0,
            'max_steps': 15,
            'full_page_screenshot': False,
            'use_vision': True,
            'allowed_domains': []
        }
        
        with get_db_session() as session:
            # Verificar se já existe configuração
            browser_config = session.query(ApiKey).filter(ApiKey.provider == 'browser_config').first()
            
            if not browser_config:
                # Criar configuração padrão
                browser_config = ApiKey(
                    provider='browser_config',
                    api_key=json.dumps(default_browser_config)
                )
                session.add(browser_config)
                session.commit()
                logger.info("Configurações padrão do navegador criadas")
            else:
                logger.info("Configurações do navegador já existem")
                
        return True
    except Exception as e:
        logger.error(f"Erro ao inicializar configurações padrão: {e}")
        return False

def main():
    """Função principal de inicialização"""
    logger.info("Iniciando processo de inicialização")
    
    # Inicializar diretórios
    init_directories()
    
    # Inicializar banco de dados
    if not init_database():
        logger.error("Falha na inicialização do banco de dados")
        sys.exit(1)
    
    # Inicializar configurações padrão
    if not init_default_config():
        logger.warning("Falha na inicialização das configurações padrão")
    
    logger.info("Inicialização concluída com sucesso")

if __name__ == "__main__":
    main()