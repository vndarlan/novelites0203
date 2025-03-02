from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class Task(Base):
    """Modelo para tarefas de agente"""
    __tablename__ = "tasks"
    
    id = Column(String(32), primary_key=True)
    task = Column(Text, nullable=False)
    status = Column(String(20), default="created")  # created, running, finished, failed
    llm_provider = Column(String(50), nullable=False)
    llm_model = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)
    output = Column(Text, nullable=True)
    config = Column(Text, nullable=True)  # Configurações específicas da tarefa como JSON
    sensitive_data = Column(Text, nullable=True)  # Dados sensíveis criptografados
    
    # Relacionamento com o histórico
    history = relationship("TaskHistory", back_populates="task", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Task {self.id}: {self.status}>"

class TaskHistory(Base):
    """Modelo para histórico de tarefas"""
    __tablename__ = "task_history"
    
    task_id = Column(String(32), ForeignKey("tasks.id"), primary_key=True)
    steps = Column(Text, nullable=True)  # Armazenado como JSON
    urls = Column(Text, nullable=True)  # Armazenado como JSON
    screenshots = Column(Text, nullable=True)  # Armazenado como JSON
    errors = Column(Text, nullable=True)  # Armazenado como JSON
    
    # Métricas adicionais
    duration = Column(DateTime, nullable=True)  # Duração da execução em segundos
    memory_usage = Column(String(50), nullable=True)  # Uso de memória durante a execução
    token_usage = Column(String(50), nullable=True)  # Tokens usados pelo LLM
    
    # Relacionamento com a tarefa
    task = relationship("Task", back_populates="history")
    
    def __repr__(self):
        return f"<TaskHistory for {self.task_id}>"

class ApiKey(Base):
    """Modelo para chaves de API"""
    __tablename__ = "api_keys"
    
    provider = Column(String(50), primary_key=True)
    api_key = Column(String(512), nullable=True)  # Armazenará também objetos JSON para configurações
    
    def __repr__(self):
        return f"<ApiKey for {self.provider}>"

class CustomFunction(Base):
    """Modelo para funções personalizadas"""
    __tablename__ = "custom_functions"
    
    id = Column(String(32), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<CustomFunction {self.name}>"

class OutputFormat(Base):
    """Modelo para formatos de saída personalizados"""
    __tablename__ = "output_formats"
    
    id = Column(String(32), primary_key=True)
    name = Column(String(100), nullable=False)
    format_schema = Column(Text, nullable=False)  # JSON schema ou exemplo
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<OutputFormat {self.name}>"