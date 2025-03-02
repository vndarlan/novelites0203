import os
import base64
import json
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Any, Optional

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityManager:
    """
    Gerenciador de segurança para criptografar e descriptografar dados sensíveis.
    """
    def __init__(self, key_env_var='SECURITY_KEY'):
        """
        Inicializa o gerenciador de segurança.
        
        Args:
            key_env_var: Nome da variável de ambiente que contém a chave de segurança
        """
        # Obter chave de ambiente ou gerar uma nova
        self.key = self._get_or_create_key(key_env_var)
        self.cipher_suite = Fernet(self.key)
    
    def _get_or_create_key(self, key_env_var: str) -> bytes:
        """
        Obtém a chave de segurança da variável de ambiente ou cria uma nova.
        
        Args:
            key_env_var: Nome da variável de ambiente
            
        Returns:
            Chave de segurança em bytes
        """
        # Verificar se existe no ambiente
        env_key = os.environ.get(key_env_var)
        
        if env_key:
            try:
                # Tentar decodificar a chave
                return base64.urlsafe_b64decode(env_key)
            except Exception as e:
                logger.warning(f"Erro ao decodificar chave de ambiente: {e}")
        
        # Gerar uma nova chave
        logger.warning(f"Variável {key_env_var} não encontrada ou inválida. Gerando nova chave.")
        
        # Usar uma senha padrão e salt para derivar a chave
        # Em produção, seria melhor usar variáveis de ambiente para estes valores
        password = "default_password".encode()
        salt = b"default_salt_value"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        # Mostrar a chave gerada para salvar em variável de ambiente
        logger.info(f"Nova chave gerada. Defina {key_env_var}={key.decode()} nas variáveis de ambiente.")
        
        return key
    
    def encrypt_data(self, data: Dict[str, Any]) -> str:
        """
        Criptografa dados sensíveis.
        
        Args:
            data: Dicionário com dados sensíveis
            
        Returns:
            String criptografada em base64
        """
        try:
            # Converter para JSON
            data_json = json.dumps(data)
            
            # Criptografar
            encrypted_data = self.cipher_suite.encrypt(data_json.encode())
            
            # Converter para base64
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Erro ao criptografar dados: {e}")
            # Retornar string vazia em caso de erro
            return ""
    
    def decrypt_data(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """
        Descriptografa dados sensíveis.
        
        Args:
            encrypted_data: String criptografada em base64
            
        Returns:
            Dicionário com dados descriptografados ou None em caso de erro
        """
        try:
            # Decodificar base64
            decoded_data = base64.urlsafe_b64decode(encrypted_data)
            
            # Descriptografar
            decrypted_data = self.cipher_suite.decrypt(decoded_data).decode()
            
            # Converter de JSON para dicionário
            return json.loads(decrypted_data)
        except Exception as e:
            logger.error(f"Erro ao descriptografar dados: {e}")
            return None
    
    def mask_sensitive_data(self, text: str, sensitive_data: Dict[str, str]) -> str:
        """
        Substitui dados sensíveis em um texto por placeholders.
        
        Args:
            text: Texto original
            sensitive_data: Dicionário com {placeholder: valor_sensível}
            
        Returns:
            Texto com dados sensíveis substituídos por placeholders
        """
        if not text or not sensitive_data:
            return text
        
        masked_text = text
        
        # Substituir valores sensíveis por placeholders
        for placeholder, value in sensitive_data.items():
            if value and value in masked_text:
                masked_text = masked_text.replace(value, f"[{placeholder}]")
        
        return masked_text
    
    def unmask_sensitive_data(self, text: str, sensitive_data: Dict[str, str]) -> str:
        """
        Substitui placeholders em um texto pelos dados sensíveis correspondentes.
        
        Args:
            text: Texto com placeholders
            sensitive_data: Dicionário com {placeholder: valor_sensível}
            
        Returns:
            Texto com placeholders substituídos por dados sensíveis
        """
        if not text or not sensitive_data:
            return text
        
        unmasked_text = text
        
        # Substituir placeholders por valores sensíveis
        for placeholder, value in sensitive_data.items():
            unmasked_text = unmasked_text.replace(f"[{placeholder}]", value)
            # Também substituir o placeholder sem colchetes
            unmasked_text = unmasked_text.replace(placeholder, value)
        
        return unmasked_text

# Instância global do gerenciador de segurança
security_manager = SecurityManager()