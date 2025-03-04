import json
import logging
from typing import Dict, Any, Optional

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SensitiveDataManager:
    """
    Gerenciador de dados sensíveis para o agente.
    
    Esta classe fornece métodos para armazenar, recuperar e processar
    dados sensíveis como senhas e tokens de acesso.
    """
    def __init__(self, security_manager=None):
        """
        Inicializa o gerenciador de dados sensíveis.
        
        Args:
            security_manager: Instância do SecurityManager para criptografia
        """
        from utils.security import security_manager as default_security_manager
        self.security_manager = security_manager or default_security_manager
        self.sensitive_placeholders = {}
    
    def add_sensitive_data(self, data: Dict[str, str]) -> None:
        """
        Adiciona dados sensíveis ao gerenciador.
        
        Args:
            data: Dicionário com {placeholder: valor_sensível}
        """
        if not data:
            return
            
        self.sensitive_placeholders.update(data)
        logger.info(f"Adicionados {len(data)} itens de dados sensíveis")
    
    def store_sensitive_data(self, task_id: str, data: Dict[str, str]) -> str:
        """
        Armazena dados sensíveis para uma tarefa específica.
        
        Args:
            task_id: ID da tarefa
            data: Dicionário com dados sensíveis
            
        Returns:
            String criptografada com os dados
        """
        if not data:
            return ""
        
        # Criptografar dados
        encrypted_data = self.security_manager.encrypt_data(data)
        
        # Armazenar no gerenciador para uso na sessão atual
        self.add_sensitive_data(data)
        
        return encrypted_data
    
    def load_sensitive_data(self, encrypted_data: str) -> Dict[str, str]:
        """
        Carrega dados sensíveis a partir de uma string criptografada.
        
        Args:
            encrypted_data: String criptografada
            
        Returns:
            Dicionário com dados sensíveis
        """
        if not encrypted_data:
            return {}
        
        # Descriptografar dados
        data = self.security_manager.decrypt_data(encrypted_data) or {}
        
        # Armazenar no gerenciador para uso na sessão atual
        self.add_sensitive_data(data)
        
        return data
    
    def mask_prompt(self, text: str) -> str:
        """
        Substitui dados sensíveis em um prompt por placeholders.
        
        Args:
            text: Prompt original
            
        Returns:
            Prompt com dados sensíveis substituídos
        """
        if not text or not self.sensitive_placeholders:
            return text
        
        masked_text = text
        
        # Substituir valores sensíveis por placeholders
        for placeholder, value in self.sensitive_placeholders.items():
            if value and value in masked_text:
                masked_text = masked_text.replace(value, f"[{placeholder}]")
        
        return masked_text
    
    def unmask_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitui placeholders em parâmetros de ação pelos valores sensíveis.
        
        Args:
            action_name: Nome da ação
            params: Parâmetros da ação
            
        Returns:
            Parâmetros com placeholders substituídos
        """
        if not params or not self.sensitive_placeholders:
            return params
        
        unmasked_params = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                # Verificar se o valor é um placeholder
                for placeholder, sensitive_value in self.sensitive_placeholders.items():
                    placeholder_pattern = f"[{placeholder}]"
                    
                    if placeholder_pattern in value:
                        value = value.replace(placeholder_pattern, sensitive_value)
                    elif placeholder == value:
                        value = sensitive_value
                
                unmasked_params[key] = value
            else:
                unmasked_params[key] = value
        
        return unmasked_params
    
    def filter_page_content(self, content: str) -> str:
        """
        Remove dados sensíveis do conteúdo da página antes de enviá-lo ao LLM.
        
        Args:
            content: Conteúdo da página
            
        Returns:
            Conteúdo com dados sensíveis substituídos por placeholders
        """
        if not content or not self.sensitive_placeholders:
            return content
        
        filtered_content = content
        
        # Substituir valores sensíveis por placeholders
        for placeholder, value in self.sensitive_placeholders.items():
            if value and value in filtered_content:
                filtered_content = filtered_content.replace(value, f"[{placeholder}]")
        
        return filtered_content
    
    def get_placeholder_description(self) -> str:
        """
        Gera uma descrição dos placeholders para o prompt do sistema.
        
        Returns:
            Descrição dos placeholders
        """
        if not self.sensitive_placeholders:
            return ""
        
        description = "DADOS SENSÍVEIS:\n"
        description += "Os seguintes placeholders serão usados para proteger dados sensíveis:\n"
        
        for placeholder in self.sensitive_placeholders.keys():
            description += f"- [{placeholder}]: Utilize este placeholder quando precisar referenciar este dado sensível\n"
        
        description += "\nNUNCA tente adivinhar ou descobrir os valores reais destes dados. Use sempre os placeholders."
        
        return description

# Criar instância global do gerenciador
sensitive_data_manager = SensitiveDataManager()