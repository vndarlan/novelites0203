import os
import asyncio
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
        
        @self.action("Perguntar ao usuário")
        def ask_human(question: str) -> ActionResult:
            """Pergunta ao usuário e retorna a resposta"""
            import streamlit as st
            
            st.write(f"🤖 **O agente está perguntando:** {question}")
            answer = st.text_input("Sua resposta:", key=f"user_input_{hash(question)}")
            submit = st.button("Enviar Resposta", key=f"submit_{hash(question)}")
            
            if submit and answer:
                return ActionResult(extracted_content=f"Resposta: {answer}")
            elif submit:
                return ActionResult(success=False, error="Resposta vazia. Por favor, forneça uma resposta.")
            else:
                return ActionResult(success=False, error="Aguardando resposta do usuário...")
        
        @self.action("Fazer upload de arquivo")
        async def upload_file(browser, selector: str, file_path: str = None) -> ActionResult:
            """Faz upload de um arquivo para um elemento na página"""
            try:
                # Se file_path não for fornecido, permitir que o usuário faça upload
                if not file_path:
                    import streamlit as st
                    
                    st.write("🤖 **O agente precisa fazer upload de um arquivo**")
                    uploaded_file = st.file_uploader("Escolha um arquivo para upload", key=f"file_upload_{hash(selector)}")
                    
                    if uploaded_file:
                        # Criar arquivo temporário
                        temp_dir = "temp_uploads"
                        os.makedirs(temp_dir, exist_ok=True)
                        
                        file_path = os.path.join(temp_dir, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        # Realizar upload usando o navegador
                        current_page = browser.get_current_page()
                        await current_page.set_input_files(selector, file_path)
                        
                        return ActionResult(extracted_content=f"Arquivo '{uploaded_file.name}' enviado com sucesso")
                    else:
                        return ActionResult(success=False, error="Aguardando upload do arquivo...")
                else:
                    # Se file_path foi fornecido, usar diretamente
                    if os.path.exists(file_path):
                        current_page = browser.get_current_page()
                        await current_page.set_input_files(selector, file_path)
                        return ActionResult(extracted_content=f"Arquivo '{os.path.basename(file_path)}' enviado com sucesso")
                    else:
                        return ActionResult(success=False, error=f"Arquivo não encontrado: {file_path}")
            
            except Exception as e:
                logger.error(f"Erro ao fazer upload de arquivo: {str(e)}")
                return ActionResult(success=False, error=f"Erro ao fazer upload: {str(e)}")
        
        @self.action("Notificar usuário")
        def notify_user(message: str, type: str = "info") -> ActionResult:
            """Exibe uma notificação para o usuário"""
            import streamlit as st
            
            if type.lower() == "success":
                st.success(message)
            elif type.lower() == "error":
                st.error(message)
            elif type.lower() == "warning":
                st.warning(message)
            else:
                st.info(message)
            
            return ActionResult(extracted_content=f"Notificação exibida: {message}")
        
        @self.action("Salvar resultado em arquivo")
        async def save_to_file(content: str, filename: str = "resultado.txt") -> ActionResult:
            """Salva conteúdo em um arquivo"""
            try:
                save_dir = "downloads"
                os.makedirs(save_dir, exist_ok=True)
                
                file_path = os.path.join(save_dir, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                return ActionResult(
                    success=True,
                    extracted_content=f"Conteúdo salvo em {file_path}"
                )
            except Exception as e:
                logger.error(f"Erro ao salvar arquivo: {str(e)}")
                return ActionResult(
                    success=False,
                    error=f"Erro ao salvar arquivo: {str(e)}"
                )
        
        @self.action("Extrair tabelas da página")
        async def extract_tables(browser) -> ActionResult:
            """Extrai todas as tabelas da página atual"""
            try:
                current_page = browser.get_current_page()
                
                # Usar JavaScript para extrair tabelas
                tables = await current_page.evaluate("""() => {
                    const tables = Array.from(document.querySelectorAll('table'));
                    return tables.map((table, index) => {
                        const rows = Array.from(table.querySelectorAll('tr'));
                        
                        const tableData = rows.map(row => {
                            const cells = Array.from(row.querySelectorAll('th, td'));
                            return cells.map(cell => cell.innerText.trim());
                        });
                        
                        return {
                            tableIndex: index,
                            tableData: tableData
                        };
                    });
                }""")
                
                if not tables:
                    return ActionResult(
                        success=True,
                        extracted_content="Nenhuma tabela encontrada na página."
                    )
                
                # Formatar tabelas para visualização
                formatted_tables = []
                for table in tables:
                    table_index = table.get('tableIndex', 0)
                    table_data = table.get('tableData', [])
                    
                    if not table_data:
                        continue
                    
                    # Calcular largura máxima para cada coluna
                    col_widths = []
                    for row in table_data:
                        while len(col_widths) < len(row):
                            col_widths.append(0)
                        
                        for i, cell in enumerate(row):
                            col_widths[i] = max(col_widths[i], len(cell))
                    
                    # Formatar tabela
                    formatted_table = f"\nTabela {table_index + 1}:\n"
                    
                    for i, row in enumerate(table_data):
                        row_str = "| "
                        
                        for j, cell in enumerate(row):
                            if j < len(col_widths):
                                row_str += cell.ljust(col_widths[j]) + " | "
                        
                        formatted_table += row_str + "\n"
                        
                        # Adicionar linha de separação após o cabeçalho
                        if i == 0:
                            separator = "| "
                            for j, width in enumerate(col_widths):
                                separator += "-" * width + " | "
                            formatted_table += separator + "\n"
                    
                    formatted_tables.append(formatted_table)
                
                return ActionResult(
                    success=True,
                    extracted_content="Tabelas extraídas:\n" + "\n".join(formatted_tables)
                )
            
            except Exception as e:
                logger.error(f"Erro ao extrair tabelas: {str(e)}")
                return ActionResult(
                    success=False,
                    error=f"Erro ao extrair tabelas: {str(e)}"
                )
    
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
                    result = await func(browser=browser, **params)
                else:
                    result = func(browser=browser, **params)
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

# Instância global do controller
controller = Controller()