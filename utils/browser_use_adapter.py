import asyncio
import json
import logging
import base64
from typing import Dict, Any, Optional, List

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BrowserUseAdapter:
    """
    Adaptador para integração com o Browser-use.
    
    Esta classe fornece uma interface para usar o Browser-use como um módulo
    ou simular sua funcionalidade quando não está instalado.
    """
    def __init__(self):
        self.browser_use_available = False
        
        # Tentar importar Browser-use
        try:
            from browser_use import Agent, Browser, BrowserConfig
            self.browser_use_available = True
            self.Agent = Agent
            self.Browser = Browser
            self.BrowserConfig = BrowserConfig
            logger.info("Browser-use importado com sucesso")
        except ImportError:
            logger.warning("Browser-use não encontrado, usando implementação interna")
    
    def create_llm_from_config(self, llm_provider: str, llm_model: str, api_key: str, endpoint: Optional[str] = None):
        """
        Cria um objeto LLM com base na configuração fornecida.
        
        Args:
            llm_provider: Provedor de LLM (openai, anthropic, etc.)
            llm_model: Nome do modelo
            api_key: Chave de API
            endpoint: Endpoint para Azure OpenAI
        
        Returns:
            Objeto LLM compatível com LangChain
        """
        if not self.browser_use_available:
            logger.error("Browser-use não disponível, não é possível criar LLM")
            return None
        
        try:
            if llm_provider == 'openai':
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=llm_model,
                    temperature=0.0,
                    api_key=api_key
                )
            
            elif llm_provider == 'anthropic':
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model_name=llm_model,
                    temperature=0.0,
                    api_key=api_key,
                    timeout=100  # Aumentar para tarefas complexas
                )
            
            elif llm_provider == 'azure':
                from langchain_openai import AzureChatOpenAI
                from pydantic import SecretStr
                return AzureChatOpenAI(
                    model=llm_model,
                    api_version='2024-10-21',
                    azure_endpoint=endpoint or '',
                    api_key=SecretStr(api_key)
                )
            
            elif llm_provider == 'gemini':
                from langchain_google_genai import ChatGoogleGenerativeAI
                from pydantic import SecretStr
                return ChatGoogleGenerativeAI(
                    model=llm_model,
                    api_key=SecretStr(api_key)
                )
            
            elif llm_provider == 'deepseek':
                from langchain_openai import ChatOpenAI
                from pydantic import SecretStr
                return ChatOpenAI(
                    base_url='https://api.deepseek.com/v1',
                    model=llm_model,
                    api_key=SecretStr(api_key)
                )
            
            elif llm_provider == 'ollama':
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=llm_model,
                    num_ctx=32000
                )
            
            else:
                logger.error(f"Provedor LLM não suportado: {llm_provider}")
                return None
            
        except Exception as e:
            logger.error(f"Erro ao criar LLM {llm_provider}/{llm_model}: {str(e)}")
            return None
    
    async def run_agent_with_browser_use(self, task_id: str, task_instructions: str, 
                                        llm_config: Dict[str, Any], browser_config: Dict[str, Any],
                                        sensitive_data: Optional[Dict[str, str]] = None,
                                        initial_actions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Executa uma tarefa usando o Browser-use.
        
        Args:
            task_id: ID da tarefa
            task_instructions: Instruções da tarefa
            llm_config: Configuração do LLM
            browser_config: Configuração do navegador
            sensitive_data: Dados sensíveis
            initial_actions: Ações iniciais
        
        Returns:
            Resultado da execução
        """
        if not self.browser_use_available:
            logger.error("Browser-use não disponível, usando implementação interna")
            # Usar a implementação interna do agent_runner.py
            from utils.agent_runner import run_agent_task
            
            # Preparar configuração
            llm_dict = {
                'provider': llm_config.get('provider'),
                'model': llm_config.get('model'),
                'api_key': llm_config.get('api_key'),
                'endpoint': llm_config.get('endpoint')
            }
            
            return await run_agent_task(task_id, task_instructions, llm_dict, browser_config)
        
        try:
            # Criar LLM
            llm = self.create_llm_from_config(
                llm_provider=llm_config.get('provider'),
                llm_model=llm_config.get('model'),
                api_key=llm_config.get('api_key'),
                endpoint=llm_config.get('endpoint')
            )
            
            if not llm:
                raise ValueError(f"Não foi possível criar LLM para {llm_config.get('provider')}")
            
            # Configurar o navegador
            browser_use_config = self.BrowserConfig(
                headless=browser_config.get('headless', True),
                disable_security=browser_config.get('disable_security', True),
                chrome_instance_path=browser_config.get('chrome_instance_path')
            )
            
            # Criar browser
            browser = self.Browser(config=browser_use_config)
            
            # Configurar agente
            agent_kwargs = {
                'task': task_instructions,
                'llm': llm,
                'browser': browser,
                'use_vision': browser_config.get('use_vision', True),
                'sensitive_data': sensitive_data,
                'save_conversation_path': f"logs/{task_id}.json"
            }
            
            # Adicionar ações iniciais se existirem
            if initial_actions:
                agent_kwargs['initial_actions'] = initial_actions
            
            # Criar e executar agente
            agent = self.Agent(**agent_kwargs)
            
            # Executar o agente e capturar o histórico
            history = await agent.run(max_steps=browser_config.get('max_steps', 15))
            
            # Converter o histórico do Browser-use para o formato esperado pelo nosso aplicativo
            result = {
                'status': 'finished' if history.is_done() else 'failed',
                'steps': [],
                'urls': history.urls(),
                'screenshots': history.screenshots(),
                'errors': history.errors(),
                'output': history.final_result() or ""
            }
            
            # Converter os passos
            for i, action in enumerate(history.model_actions()):
                step = {
                    'step': i + 1,
                    'evaluation_previous_goal': action.get('reasoning', ''),
                    'next_goal': f"{action.get('name')}({', '.join(str(p) for p in action.get('args', []))})"
                }
                result['steps'].append(step)
            
            # Fechar o navegador
            await browser.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao executar agente com Browser-use: {str(e)}")
            return {
                'status': 'failed',
                'steps': [],
                'urls': [],
                'screenshots': [],
                'errors': [str(e)],
                'output': f"Erro na execução com Browser-use: {str(e)}"
            }