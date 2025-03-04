import os
import sys
import logging
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
    "static/screenshots",
    "static/recordings",  # Nova pasta para gravações
    "downloads",          # Pasta para arquivos salvos pelo agente
    "temp_uploads"        # Pasta para uploads temporários
]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Diretório criado: {directory}")

def init_database():
    """Inicializa o banco de dados"""
    try:
        # Verificar se temos conexão com o banco de dados
        if not os.environ.get('DATABASE_URL'):
            logger.warning("Variável DATABASE_URL não encontrada. Pulando inicialização do banco de dados.")
            return False
            
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
        # Verificar se a inicialização do banco de dados foi bem-sucedida
        if not os.environ.get('DATABASE_URL'):
            logger.warning("Variável DATABASE_URL não encontrada. Pulando configurações padrão.")
            return False
            
        # Importações necessárias
        import json
        from db.database import get_db_session
        from db.models import ApiKey
        
        default_browser_config = {
            'headless': False,  # Alterado para False por padrão para visualizar o navegador
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
            'allowed_domains': [],
            'save_recording': True,  # Nova opção para gravar a execução
            'recording_path': 'static/recordings',  # Caminho para salvar as gravações
            'show_browser': True  # Nova opção para mostrar o navegador durante a execução
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
    
    # Verificar o ambiente
    is_railway = bool(os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_PUBLIC_DOMAIN'))
    if is_railway:
        logger.info("Ambiente Railway detectado")
    else:
        logger.info("Executando em ambiente local")
    
    # Inicializar diretórios
    init_directories()
    
    # Verificar se estamos apenas construindo a imagem
    if os.environ.get('RAILWAY_BUILD_PHASE'):
        logger.info("Fase de build detectada. Pulando inicialização do banco de dados.")
        return
    
    # Inicializar banco de dados apenas se estivermos executando o aplicativo (não na fase de build)
    if not init_database():
        logger.warning("Falha na inicialização do banco de dados, mas continuando...")
    
    # Inicializar configurações padrão
    if not init_default_config():
        logger.warning("Falha na inicialização das configurações padrão, mas continuando...")
    
    logger.info("Inicialização concluída")

if __name__ == "__main__":
    main()