import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union
from pydantic import BaseModel, create_model

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ActionResult:
    """Classe para representar o resultado de uma ação do controller"""
    def __init__(self, extracted_content: Optional[str] = None, success: bool = True, error: Optional[str] = None):
        self.extracted_content = extracted_content
        self.success = success
        self.error = error
    
    def __str__(self) -> str:
        if self.success:
            return self.extracted_content or "Ação executada com sucesso"
        else:
            return f"Erro: {self.error}"

class Controller:
    """
    Controlador de ações para o agente. Permite registrar funções personalizadas
    que podem ser chamadas pelo agente durante a execução.
    """
    def __init__(self, output_model: Optional[Type[BaseModel]] = None, exclude_actions: Optional[List[str]] = None):
        self.actions = {}
        self.descriptions = {}
        self.param_models = {}
        self.output_model = output_model
        self.exclude_actions = exclude_actions or []
        
        # Registrar ações padrão
        self._register_default_actions()
    
    def _register_default_actions(self):
        """Registra ações padrão que estarão disponíveis para todos os controladores"""
        
        @self.action("Exibir mensagem de depuração")
        def debug_message(message: str) -> ActionResult:
            """Exibe uma mensagem de depuração no console"""
            logger.info(f"Depuração: {message}")
            return ActionResult(extracted_content=f"Mensagem exibida: {message}")
    
    def action(self, description: str, param_model: Optional[Type[BaseModel]] = None):
        """
        Decorador para registrar uma nova ação no controlador.
        
        Args:
            description: Descrição da ação que será mostrada ao LLM
            param_model: Modelo Pydantic opcional para validar os parâmetros da ação
        """
        def decorator(func):
            action_name = func.__name__
            
            # Verificar se ação deve ser excluída
            if action_name in self.exclude_actions:
                logger.info(f"Ação {action_name} excluída conforme configuração")
                return func
            
            # Se não for fornecido um modelo de parâmetros, criar um automaticamente
            if param_model is None:
                # Obter os parâmetros da função
                sig = inspect.signature(func)
                
                # Criar um modelo Pydantic para os parâmetros
                fields = {}
                for name, param in sig.parameters.items():
                    # Ignorar parâmetros especiais como self, cls, browser, etc.
                    if name in ['self', 'cls', 'browser', 'context']:
                        continue
                    
                    # Obter tipo e valor padrão
                    field_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
                    default_value = param.default if param.default != inspect.Parameter.empty else ...
                    
                    fields[name] = (field_type, default_value)
                
                # Criar modelo dinâmico
                action_param_model = create_model(f"{action_name.title()}Params", **fields)
                self.param_models[action_name] = action_param_model
            else:
                self.param_models[action_name] = param_model
            
            # Registrar a ação
            self.actions[action_name] = func
            self.descriptions[action_name] = description
            
            logger.info(f"Ação registrada: {action_name} - {description}")
            
            return func
        
        return decorator
    
    def get_function_descriptions(self) -> List[Dict[str, Any]]:
        """
        Retorna as descrições de todas as funções registradas em um formato
        adequado para o LLM.
        """
        function_descriptions = []
        
        for action_name, func in self.actions.items():
            if action_name in self.exclude_actions:
                continue
            
            param_model = self.param_models.get(action_name)
            if param_model:
                # Obter esquema JSON do modelo de parâmetros
                schema = param_model.schema()
                
                # Criar descrição da função
                function_description = {
                    "name": action_name,
                    "description": self.descriptions.get(action_name, ""),
                    "parameters": schema
                }
                
                function_descriptions.append(function_description)
        
        return function_descriptions
    
    def get_output_schema(self) -> Optional[Dict[str, Any]]:
        """Retorna o esquema JSON do modelo de saída, se definido"""
        if self.output_model:
            return self.output_model.schema()
        return None
    
    async def execute_action(self, action_name: str, params: Dict[str, Any], browser=None) -> ActionResult:
        """
        Executa uma ação registrada com os parâmetros fornecidos.
        
        Args:
            action_name: Nome da ação a ser executada
            params: Parâmetros da ação
            browser: Instância do navegador (opcional)
        
        Returns:
            Resultado da ação
        """
        if action_name not in self.actions:
            return ActionResult(
                success=False,
                error=f"Ação não encontrada: {action_name}"
            )
        
        func = self.actions[action_name]
        
        try:
            # Verificar se a função espera o parâmetro 'browser'
            sig = inspect.signature(func)
            if 'browser' in sig.parameters and browser is not None:
                # Adicionar browser aos parâmetros
                if inspect.iscoroutinefunction(func):
                    result = await func(**params, browser=browser)
                else:
                    result = func(**params, browser=browser)
            else:
                # Chamar sem browser
                if inspect.iscoroutinefunction(func):
                    result = await func(**params)
                else:
                    result = func(**params)
            
            # Se o resultado já for um ActionResult, retorná-lo
            if isinstance(result, ActionResult):
                return result
            
            # Caso contrário, criar um ActionResult com o conteúdo extraído
            return ActionResult(extracted_content=str(result))
        
        except Exception as e:
            logger.error(f"Erro ao executar ação {action_name}: {str(e)}")
            return ActionResult(
                success=False,
                error=f"Erro ao executar {action_name}: {str(e)}"
            )