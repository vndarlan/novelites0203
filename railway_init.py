import os
import logging
import time
import sys

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("railway_init.log")
    ]
)
logger = logging.getLogger(__name__)

def check_railway_environment():
    """Verifica se estamos rodando no Railway"""
    is_railway = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    if is_railway:
        logger.info("Ambiente Railway detectado")
    else:
        logger.info("Executando em ambiente local")
    return bool(is_railway)

def run_initialization():
    """Executa todos os passos de inicialização"""
    # Definir variáveis de ambiente comuns se não existirem
    if not os.environ.get('TZ'):
        os.environ['TZ'] = 'America/Sao_Paulo'
        logger.info("Definido fuso horário: America/Sao_Paulo")
    
    try:
        # Criar diretórios necessários
        from init_app import init_directories
        init_directories()
        logger.info("Diretórios inicializados")
        
        # Verificar banco de dados
        from utils.db_migration import run_migration
        
        logger.info("Iniciando verificação de banco de dados e migração...")
        success = run_migration()
        
        if success:
            logger.info("Banco de dados verificado e atualizado com sucesso")
        else:
            logger.warning("Problemas ao verificar/atualizar banco de dados")
        
        # Inicializar configurações padrão
        from init_app import init_default_config
        init_default_config()
        logger.info("Configurações padrão inicializadas")
        
        # Configurar healthcheck para Railway
        if check_railway_environment():
            try:
                logger.info("Configurando healthcheck para Railway")
                from utils.health_check import setup_healthcheck
                setup_healthcheck()
                logger.info("Healthcheck configurado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao configurar healthcheck: {e}")
        
        # Configurar tarefa de manutenção
        try:
            logger.info("Configurando tarefa de manutenção")
            from utils.maintenance import schedule_maintenance
            schedule_maintenance()
            logger.info("Tarefa de manutenção configurada")
        except Exception as e:
            logger.error(f"Erro ao configurar tarefa de manutenção: {e}")
        
        # Verificar se o Playwright está instalado
        try:
            logger.info("Verificando instalação do Playwright")
            from playwright.async_api import async_playwright
            logger.info("Playwright importado com sucesso")
            
            # Verificar se o navegador está instalado
            import subprocess
            logger.info("Verificando instalação do navegador")
            result = subprocess.run(["python", "-m", "playwright", "install", "chromium"], 
                                   capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Navegador Chromium instalado com sucesso")
            else:
                logger.warning(f"Problemas ao instalar Chromium: {result.stderr}")
        except Exception as e:
            logger.error(f"Erro ao verificar Playwright: {e}")
        
        # Verificar integração com Browser-use
        try:
            logger.info("Verificando integração com Browser-use")
            from utils.browser_use_adapter import BrowserUseAdapter
            adapter = BrowserUseAdapter()
            if adapter.browser_use_available:
                logger.info("Browser-use disponível e integrado")
            else:
                logger.info("Browser-use não disponível, usando implementação interna")
        except Exception as e:
            logger.error(f"Erro ao verificar integração com Browser-use: {e}")
        
        logger.info("Inicialização concluída com sucesso")
        return True
    
    except Exception as e:
        logger.error(f"Erro geral na inicialização: {e}")
        return False

if __name__ == "__main__":
    logger.info("Iniciando script de inicialização do Railway")
    
    # Aguardar um pouco para garantir que todos os serviços estejam prontos
    if check_railway_environment():
        logger.info("Aguardando 5 segundos para inicialização completa...")
        time.sleep(5)
    
    # Executar inicialização
    success = run_initialization()
    
    if success:
        logger.info("Inicialização concluída com sucesso")
        sys.exit(0)
    else:
        logger.error("Falha na inicialização")
        sys.exit(1)