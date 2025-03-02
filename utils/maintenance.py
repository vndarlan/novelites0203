import os
import logging
import shutil
from datetime import datetime, timedelta
from typing import List, Optional
import json

# Importações internas
from db.database import get_db_session
from db.models import Task, TaskHistory

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MaintenanceManager:
    """
    Gerenciador de manutenção para limpeza de dados antigos e backup.
    """
    def __init__(self, screenshots_dir: str = 'static/screenshots', max_age_days: int = 30):
        """
        Inicializa o gerenciador de manutenção.
        
        Args:
            screenshots_dir: Diretório onde os screenshots são armazenados
            max_age_days: Idade máxima em dias para manter tarefas e arquivos
        """
        self.screenshots_dir = screenshots_dir
        self.max_age_days = max_age_days
    
    def clean_old_tasks(self, days: Optional[int] = None) -> int:
        """
        Remove tarefas antigas do banco de dados.
        
        Args:
            days: Idade máxima em dias (usa o valor padrão se None)
            
        Returns:
            Número de tarefas removidas
        """
        if days is None:
            days = self.max_age_days
        
        # Calcular data limite
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            with get_db_session() as session:
                # Encontrar tarefas antigas
                old_tasks = session.query(Task).filter(Task.created_at < cutoff_date).all()
                
                # Capturar IDs para relatório
                task_ids = [task.id for task in old_tasks]
                
                # Remover tarefas antigas (o histórico será removido em cascata)
                count = len(old_tasks)
                for task in old_tasks:
                    session.delete(task)
                
                session.commit()
                
                logger.info(f"Removidas {count} tarefas antigas: {task_ids}")
                return count
        
        except Exception as e:
            logger.error(f"Erro ao limpar tarefas antigas: {e}")
            return 0
    
    def clean_old_screenshots(self, days: Optional[int] = None) -> int:
        """
        Remove screenshots antigos que não estão mais vinculados a tarefas.
        
        Args:
            days: Idade máxima em dias (usa o valor padrão se None)
            
        Returns:
            Número de arquivos removidos
        """
        if days is None:
            days = self.max_age_days
        
        if not os.path.exists(self.screenshots_dir):
            logger.warning(f"Diretório de screenshots não existe: {self.screenshots_dir}")
            return 0
        
        # Calcular data limite para arquivos
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # Obter lista de screenshots usados em tarefas
            used_screenshots = []
            with get_db_session() as session:
                histories = session.query(TaskHistory).all()
                
                for history in histories:
                    if history.screenshots:
                        try:
                            screenshots = json.loads(history.screenshots)
                            used_screenshots.extend(screenshots)
                        except:
                            pass
            
            # Listar todos os arquivos no diretório
            all_files = []
            for filename in os.listdir(self.screenshots_dir):
                filepath = os.path.join(self.screenshots_dir, filename)
                if os.path.isfile(filepath):
                    all_files.append(filepath)
            
            # Identificar arquivos não usados ou antigos
            count = 0
            for filepath in all_files:
                # Verificar se o arquivo é antigo
                file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                
                # Remover se for antigo e não estiver sendo usado
                if file_time < cutoff_date and filepath not in used_screenshots:
                    try:
                        os.remove(filepath)
                        count += 1
                    except Exception as e:
                        logger.error(f"Erro ao remover arquivo {filepath}: {e}")
            
            logger.info(f"Removidos {count} screenshots antigos")
            return count
        
        except Exception as e:
            logger.error(f"Erro ao limpar screenshots antigos: {e}")
            return 0
    
    def create_backup(self, backup_dir: str = 'backups') -> Optional[str]:
        """
        Cria um backup do banco de dados e screenshots.
        
        Args:
            backup_dir: Diretório onde os backups serão armazenados
            
        Returns:
            Caminho do arquivo de backup ou None em caso de erro
        """
        # Verificar se o diretório existe
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Nome do arquivo de backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        try:
            # Criar arquivo zip
            shutil.make_archive(
                os.path.splitext(backup_path)[0],  # Nome base sem extensão
                'zip',  # Formato
                './',  # Diretório raiz
                # Lista de diretórios para incluir
                include_dir_names=[self.screenshots_dir, 'db']
            )
            
            logger.info(f"Backup criado em {backup_path}")
            return backup_path
        
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            return None
    
    def run_maintenance(self) -> Dict[str, int]:
        """
        Executa rotina completa de manutenção.
        
        Returns:
            Dicionário com resultados das operações
        """
        results = {
            'tasks_removed': 0,
            'screenshots_removed': 0,
            'backup_created': 0
        }
        
        # Limpar tarefas antigas
        results['tasks_removed'] = self.clean_old_tasks()
        
        # Limpar screenshots antigos
        results['screenshots_removed'] = self.clean_old_screenshots()
        
        # Criar backup
        backup_path = self.create_backup()
        results['backup_created'] = 1 if backup_path else 0
        
        return results

# Função para criar uma tarefa cron de manutenção
def schedule_maintenance():
    """
    Configura uma tarefa cron para executar manutenção periódica.
    
    Nota: Esta função pode ser chamada no script de inicialização.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        # Criar scheduler
        scheduler = BackgroundScheduler()
        
        # Criar gerenciador de manutenção
        manager = MaintenanceManager()
        
        # Adicionar tarefa para executar todos os dias às 3:00 da manhã
        scheduler.add_job(
            manager.run_maintenance,
            trigger=CronTrigger(hour=3, minute=0),
            id='maintenance_job',
            replace_existing=True
        )
        
        # Iniciar scheduler
        scheduler.start()
        
        logger.info("Manutenção agendada com sucesso")
        return True
    
    except Exception as e:
        logger.error(f"Erro ao agendar manutenção: {e}")
        return False