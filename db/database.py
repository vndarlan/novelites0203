import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

# Função para obter a string de conexão do banco de dados
def get_database_url():
    # Verificar se estamos na fase de build
    if os.environ.get('RAILWAY_BUILD_PHASE'):
        logger.info("Fase de build detectada, usando SQLite temporário")
        return 'sqlite:///./test_build.db'
    
    # Verificar se estamos no Railway
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # No Railway, a variável DATABASE_URL estará disponível
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            logger.warning("DATABASE_URL não definida no Railway, usando SQLite")
            return 'sqlite:///./site_agente.db'
        
        # O Railway usa postgres://, mas SQLAlchemy precisa de postgresql://
        if database_url and database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        logger.info("Usando banco de dados do Railway")
        return database_url
    else:
        # Para desenvolvimento local, usar SQLite
        logger.info("Usando banco de dados SQLite local")
        return 'sqlite:///./site_agente.db'

# Configuração do engine do SQLAlchemy
def create_db_engine():
    database_url = get_database_url()
    logger.info(f"Criando engine com URL: {database_url}")
    
    try:
        # Criar engine com opções adequadas para PostgreSQL
        if database_url.startswith('postgresql'):
            return create_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,  # Reciclar conexões a cada 30 minutos
                echo=False  # Definir como True para debug
            )
        else:
            # SQLite para desenvolvimento local
            return create_engine(
                database_url,
                connect_args={"check_same_thread": False},  # Necessário para SQLite
                echo=False
            )
    except Exception as e:
        logger.error(f"Erro ao criar engine: {str(e)}")
        
        # Fallback para SQLite em memória em caso de erro
        if os.environ.get('RAILWAY_BUILD_PHASE'):
            logger.warning("Usando SQLite em memória como fallback durante build")
            return create_engine('sqlite:///:memory:', connect_args={"check_same_thread": False})
        
        # Relancar a exceção se não estiver na fase de build
        raise

# Engine global
try:
    engine = create_db_engine()
except Exception as e:
    logger.error(f"Erro ao criar engine do banco de dados: {e}")
    # Em modo de build, criar um engine dummy para permitir que a construção continue
    if os.environ.get('RAILWAY_BUILD_PHASE'):
        logger.warning("Criando engine dummy para fase de build")
        engine = create_engine('sqlite:///:memory:')
    else:
        raise

# Fábrica de sessões
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

# Função para inicializar o banco de dados
def init_db():
    try:
        logger.info("Inicializando banco de dados...")
        
        # Importar modelos para criar tabelas
        from db.models import Task, TaskHistory, ApiKey
        
        # Criar tabelas
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas criadas com sucesso")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        
        # Não lançar exceção durante a fase de build
        if os.environ.get('RAILWAY_BUILD_PHASE'):
            logger.warning("Ignorando erro de inicialização durante build")
            return False
        
        raise

# Contexto de sessão para uso com 'with'
def get_db_session():
    session = SessionLocal()
    try:
        return session
    finally:
        session.close()