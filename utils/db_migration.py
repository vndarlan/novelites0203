import logging
import json
from sqlalchemy import text, inspect
from typing import List, Dict, Any

# Importações internas
from db.database import get_db_session, engine
from db.models import Base

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DBMigrationManager:
    """
    Gerenciador de migrações de banco de dados.
    
    Esta classe fornece métodos para verificar a estrutura do banco de dados
    e realizar migrações quando necessário.
    """
    def __init__(self):
        self.inspector = inspect(engine)
    
    def get_existing_tables(self) -> List[str]:
        """
        Obtém a lista de tabelas existentes no banco de dados.
        
        Returns:
            Lista de nomes de tabelas
        """
        return self.inspector.get_table_names()
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Obtém a lista de colunas de uma tabela.
        
        Args:
            table_name: Nome da tabela
            
        Returns:
            Lista de dicionários com informações das colunas
        """
        return self.inspector.get_columns(table_name)
    
    def check_database_structure(self) -> Dict[str, Any]:
        """
        Verifica a estrutura atual do banco de dados.
        
        Returns:
            Dicionário com informações sobre o estado do banco de dados
        """
        result = {
            'tables': {},
            'missing_tables': [],
            'missing_columns': {},
            'needs_migration': False
        }
        
        # Obter tabelas existentes
        existing_tables = self.get_existing_tables()
        
        # Modelo de tabelas esperado
        expected_tables = list(Base.metadata.tables.keys())
        
        # Verificar tabelas faltantes
        for table_name in expected_tables:
            if table_name not in existing_tables:
                result['missing_tables'].append(table_name)
                result['needs_migration'] = True
            else:
                # Verificar colunas
                existing_columns = {col['name']: col for col in self.get_table_columns(table_name)}
                expected_columns = Base.metadata.tables[table_name].columns
                
                missing_columns = []
                for col_name, col in expected_columns.items():
                    if col_name not in existing_columns:
                        missing_columns.append(col_name)
                
                if missing_columns:
                    result['missing_columns'][table_name] = missing_columns
                    result['needs_migration'] = True
                
                # Adicionar informações da tabela
                result['tables'][table_name] = {
                    'existing_columns': list(existing_columns.keys()),
                    'expected_columns': list(expected_columns.keys()),
                    'missing_columns': missing_columns
                }
        
        return result
    
    def migrate_database(self) -> Dict[str, Any]:
        """
        Realiza a migração do banco de dados para a estrutura mais recente.
        
        Returns:
            Dicionário com resultados da migração
        """
        result = {
            'success': False,
            'created_tables': [],
            'altered_tables': [],
            'errors': []
        }
        
        try:
            # Verificar estrutura atual
            check_result = self.check_database_structure()
            
            if not check_result['needs_migration']:
                logger.info("Banco de dados já está atualizado")
                result['success'] = True
                return result
            
            # Criar tabelas faltantes
            for table_name in check_result['missing_tables']:
                try:
                    # Obter definição da tabela
                    table = Base.metadata.tables[table_name]
                    
                    # Criar tabela
                    table.create(engine)
                    
                    result['created_tables'].append(table_name)
                    logger.info(f"Tabela {table_name} criada com sucesso")
                except Exception as e:
                    error_msg = f"Erro ao criar tabela {table_name}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
            
            # Adicionar colunas faltantes
            for table_name, missing_columns in check_result['missing_columns'].items():
                if not missing_columns:
                    continue
                
                try:
                    # Obter definição da tabela
                    table = Base.metadata.tables[table_name]
                    
                    # Adicionar cada coluna faltante
                    with engine.begin() as conn:
                        for col_name in missing_columns:
                            col = table.columns[col_name]
                            
                            # Gerar SQL para adicionar coluna
                            type_sql = str(col.type.compile(dialect=engine.dialect))
                            nullable = "NULL" if col.nullable else "NOT NULL"
                            default = f"DEFAULT {col.default.arg}" if col.default is not None else ""
                            
                            sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {type_sql} {nullable} {default}"
                            
                            # Executar SQL
                            conn.execute(text(sql))
                            logger.info(f"Coluna {col_name} adicionada à tabela {table_name}")
                    
                    result['altered_tables'].append(table_name)
                except Exception as e:
                    error_msg = f"Erro ao alterar tabela {table_name}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
            
            # Atualizar dados se necessário (migração de dados específica)
            self._migrate_data()
            
            result['success'] = len(result['errors']) == 0
            return result
        
        except Exception as e:
            error_msg = f"Erro geral na migração: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)
            return result
    
    def _migrate_data(self):
        """
        Realiza migrações específicas de dados, se necessário.
        Esta função pode ser expandida para migrações futuras.
        """
        try:
            # Exemplo: migrar configurações do navegador
            with get_db_session() as session:
                # Verificar se existem configurações antigas
                result = session.execute(text("SELECT * FROM api_keys WHERE provider = 'browser_config'"))
                row = result.fetchone()
                
                if row and 'api_key' in row._mapping:
                    try:
                        # Tentar analisar configurações existentes
                        config = json.loads(row._mapping['api_key'])
                        
                        # Verificar se há novos campos para adicionar
                        updated = False
                        
                        if 'use_vision' not in config:
                            config['use_vision'] = True
                            updated = True
                        
                        if 'allowed_domains' not in config:
                            config['allowed_domains'] = []
                            updated = True
                        
                        if updated:
                            # Atualizar configurações
                            session.execute(
                                text("UPDATE api_keys SET api_key = :config WHERE provider = 'browser_config'"),
                                {"config": json.dumps(config)}
                            )
                            session.commit()
                            logger.info("Configurações do navegador atualizadas")
                    except:
                        logger.warning("Não foi possível analisar configurações do navegador")
        
        except Exception as e:
            logger.error(f"Erro ao migrar dados: {str(e)}")

def run_migration():
    """
    Executa a migração do banco de dados.
    
    Returns:
        True se a migração foi bem-sucedida, False caso contrário
    """
    try:
        manager = DBMigrationManager()
        result = manager.migrate_database()
        
        if result['success']:
            logger.info("Migração concluída com sucesso")
        else:
            logger.error(f"Migração falhou com erros: {result['errors']}")
        
        return result['success']
    
    except Exception as e:
        logger.error(f"Erro ao executar migração: {str(e)}")
        return False

if __name__ == "__main__":
    run_migration()