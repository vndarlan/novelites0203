# site agente novelties
import streamlit as st
import asyncio
import time
import os
import pandas as pd
from datetime import datetime
import tempfile
import json
import threading
import logging
import glob
import shutil
from typing import Dict, Any, Optional

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Iniciando app.py")

try:
    # Configuração inicial do Streamlit
    st.set_page_config(
        page_title="Gerenciador de Agentes IA",
        page_icon="🤖",
        layout="wide"
    )
    
    logger.info("Configuração do Streamlit inicializada")
except Exception as e:
    logger.error(f"Erro ao configurar Streamlit: {e}")

# IMPORTANTE: bloco removido para evitar conflito com o healthcheck separado
# Não tente inicializar o healthcheck aqui, pois agora ele é executado como processo separado

# Importações internas
try:
    logger.info("Importando módulos internos")
    from db.database import init_db, get_db_session
    from db.models import Task, TaskHistory, ApiKey
    from utils.agent_runner import run_agent_task
    from utils.helpers import format_datetime, get_status_color, generate_unique_id, get_llm_models
    from utils.sensitive_data import sensitive_data_manager
    from utils.controller import controller, ActionResult
    from utils.output_format import output_format_manager
    logger.info("Módulos internos importados com sucesso")
except ImportError as e:
    logger.error(f"Erro ao importar módulos: {e}")
    st.error(f"Erro ao importar módulos: {e}")

def delete_task(task_id):
    """Deleta uma tarefa e seu histórico do banco de dados"""
    logger.info(f"Tentando deletar tarefa {task_id}")
    
    try:
        with get_db_session() as session:
            # Buscar a tarefa (o relacionamento em cascata irá excluir o histórico automaticamente)
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                logger.warning(f"Tarefa {task_id} não encontrada para exclusão")
                return False, "Tarefa não encontrada"
            
            # Excluir a tarefa
            session.delete(task)
            session.commit()
            
            # Tentar excluir screenshots e gravação
            try:
                # Remover screenshots
                screenshot_pattern = f"static/screenshots/{task_id}_*.png"
                for screenshot in glob.glob(screenshot_pattern):
                    os.remove(screenshot)
                
                # Remover gravação
                recording_path = f"static/recordings/{task_id}.webm"
                if os.path.exists(recording_path):
                    os.remove(recording_path)
            except Exception as e:
                logger.warning(f"Erro ao remover arquivos da tarefa {task_id}: {str(e)}")
            
            logger.info(f"Tarefa {task_id} deletada com sucesso")
            return True, "Tarefa deletada com sucesso"
    
    except Exception as e:
        logger.error(f"Erro ao deletar tarefa {task_id}: {str(e)}")
        return False, f"Erro ao deletar tarefa: {str(e)}"

# Inicialização de variáveis de sessão
def init_session_state():
    """Inicializa variáveis de estado da sessão"""
    try:
        logger.info("Inicializando estado da sessão")
        if 'db_initialized' not in st.session_state:
            st.session_state.db_initialized = False
        if 'current_task' not in st.session_state:
            st.session_state.current_task = None
        if 'llm_provider' not in st.session_state:
            st.session_state.llm_provider = "openai"
        if 'llm_model' not in st.session_state:
            st.session_state.llm_model = "gpt-4o"
        if 'browser_config' not in st.session_state:
            # Carregar config do banco de dados ou usar padrão
            st.session_state.browser_config = {
                'headless': False,  # Mudado para False para visualizar o navegador
                'disable_security': True,
                'browser_window_width': 1280,
                'browser_window_height': 1100,
                'highlight_elements': True,
                'chrome_instance_path': None,
                'wait_for_network_idle': 3.0,
                'minimum_wait_page_load_time': 0.5,
                'maximum_wait_page_load_time': 5.0,
                'max_steps': 15,
                'full_page_screenshot': False,
                'use_vision': True,
                'save_recording': True,
                'recording_path': 'static/recordings',
                'show_browser': True
            }
        if 'task_running' not in st.session_state:
            st.session_state.task_running = False
        if 'task_result' not in st.session_state:
            st.session_state.task_result = None
        if 'screenshot_index' not in st.session_state:
            st.session_state.screenshot_index = 0
        if 'confirm_delete_all' not in st.session_state:
            st.session_state.confirm_delete_all = False
        if 'delete_message' not in st.session_state:
            st.session_state.delete_message = None
        if 'sensitive_data_entries' not in st.session_state:
            st.session_state.sensitive_data_entries = [("x_username", ""), ("x_password", "")]
        if 'force_rerun_task' not in st.session_state:
            st.session_state.force_rerun_task = False
        logger.info("Estado da sessão inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar estado da sessão: {e}")

# Interface Streamlit
def auth_page():
    """Página de configuração das chaves de API"""
    try:
        logger.info("Carregando página de configuração")
        st.title("🔐 Configuração das APIs")
        
        # Obter chaves atuais do banco de dados
        with get_db_session() as session:
            api_keys = {key.provider: key.api_key for key in session.query(ApiKey).all()}
            azure_endpoint = api_keys.get('azure_endpoint', '')
        
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "OpenAI", "Anthropic", "Azure OpenAI", "Gemini", "DeepSeek", "Ollama"
        ])
        
        with tab1:
            st.markdown("### Configuração OpenAI")
            openai_api_key = st.text_input(
                "API Key OpenAI", 
                type="password", 
                value=api_keys.get('openai', '')
            )
            if st.button("Salvar Chave OpenAI"):
                with get_db_session() as session:
                    key = session.query(ApiKey).filter(ApiKey.provider == 'openai').first()
                    if key:
                        key.api_key = openai_api_key
                    else:
                        key = ApiKey(provider='openai', api_key=openai_api_key)
                        session.add(key)
                    session.commit()
                st.success("Chave API OpenAI salva com sucesso!")
        
        with tab2:
            st.markdown("### Configuração Anthropic")
            anthropic_api_key = st.text_input(
                "API Key Anthropic", 
                type="password", 
                value=api_keys.get('anthropic', '')
            )
            if st.button("Salvar Chave Anthropic"):
                with get_db_session() as session:
                    key = session.query(ApiKey).filter(ApiKey.provider == 'anthropic').first()
                    if key:
                        key.api_key = anthropic_api_key
                    else:
                        key = ApiKey(provider='anthropic', api_key=anthropic_api_key)
                        session.add(key)
                    session.commit()
                st.success("Chave API Anthropic salva com sucesso!")
        
        with tab3:
            st.markdown("### Configuração Azure OpenAI")
            azure_openai_endpoint = st.text_input(
                "Azure OpenAI Endpoint", 
                value=azure_endpoint
            )
            azure_openai_key = st.text_input(
                "Azure OpenAI Key", 
                type="password", 
                value=api_keys.get('azure', '')
            )
            if st.button("Salvar Configuração Azure"):
                with get_db_session() as session:
                    # Salvar endpoint
                    endpoint_key = session.query(ApiKey).filter(ApiKey.provider == 'azure_endpoint').first()
                    if endpoint_key:
                        endpoint_key.api_key = azure_openai_endpoint
                    else:
                        endpoint_key = ApiKey(provider='azure_endpoint', api_key=azure_openai_endpoint)
                        session.add(endpoint_key)
                    
                    # Salvar chave
                    key = session.query(ApiKey).filter(ApiKey.provider == 'azure').first()
                    if key:
                        key.api_key = azure_openai_key
                    else:
                        key = ApiKey(provider='azure', api_key=azure_openai_key)
                        session.add(key)
                    
                    session.commit()
                st.success("Configuração Azure OpenAI salva com sucesso!")
        
        with tab4:
            st.markdown("### Configuração Gemini")
            gemini_api_key = st.text_input(
                "API Key Gemini", 
                type="password", 
                value=api_keys.get('gemini', '')
            )
            if st.button("Salvar Chave Gemini"):
                with get_db_session() as session:
                    key = session.query(ApiKey).filter(ApiKey.provider == 'gemini').first()
                    if key:
                        key.api_key = gemini_api_key
                    else:
                        key = ApiKey(provider='gemini', api_key=gemini_api_key)
                        session.add(key)
                    session.commit()
                st.success("Chave API Gemini salva com sucesso!")
        
        with tab5:
            st.markdown("### Configuração DeepSeek")
            deepseek_api_key = st.text_input(
                "API Key DeepSeek", 
                type="password", 
                value=api_keys.get('deepseek', '')
            )
            if st.button("Salvar Chave DeepSeek"):
                with get_db_session() as session:
                    key = session.query(ApiKey).filter(ApiKey.provider == 'deepseek').first()
                    if key:
                        key.api_key = deepseek_api_key
                    else:
                        key = ApiKey(provider='deepseek', api_key=deepseek_api_key)
                        session.add(key)
                    session.commit()
                st.success("Chave API DeepSeek salva com sucesso!")
        
        with tab6:
            st.markdown("### Configuração Ollama")
            st.info("Ollama é executado localmente e não requer chave API. Certifique-se de que o Ollama esteja instalado e em execução no servidor.")
        
        st.divider()
        
        st.markdown("### Configuração do Navegador")
        col1, col2 = st.columns(2)
        
        with col1:
            headless = st.checkbox(
                "Modo Headless (sem interface visual)", 
                value=st.session_state.browser_config['headless']
            )
            disable_security = st.checkbox(
                "Desativar segurança do navegador", 
                value=st.session_state.browser_config['disable_security'],
                help="Desativa recursos de segurança do navegador, útil para algumas automações, mas use com cautela."
            )
            highlight_elements = st.checkbox(
                "Destacar elementos interativos", 
                value=st.session_state.browser_config['highlight_elements'],
                help="Destacar elementos interativos na página com caixas coloridas."
            )
        
        with col2:
            browser_window_width = st.number_input(
                "Largura da janela do navegador", 
                min_value=800, 
                max_value=2560, 
                value=st.session_state.browser_config['browser_window_width']
            )
            browser_window_height = st.number_input(
                "Altura da janela do navegador", 
                min_value=600, 
                max_value=2160, 
                value=st.session_state.browser_config['browser_window_height']
            )
        
        if st.button("Salvar Configurações do Navegador"):
            # Atualizar sessão
            browser_config = {
                'headless': headless,
                'disable_security': disable_security,
                'browser_window_width': browser_window_width,
                'browser_window_height': browser_window_height,
                'highlight_elements': highlight_elements,
                'chrome_instance_path': st.session_state.browser_config.get('chrome_instance_path'),
                'wait_for_network_idle': 3.0,
                'minimum_wait_page_load_time': 0.5,
                'maximum_wait_page_load_time': 5.0,
                'max_steps': 15,
                'full_page_screenshot': False,
                'use_vision': True,
                'save_recording': True,
                'recording_path': 'static/recordings',
                'show_browser': not headless
            }
            st.session_state.browser_config = browser_config
            
            # Salvar no banco de dados como JSON
            with get_db_session() as session:
                key = session.query(ApiKey).filter(ApiKey.provider == 'browser_config').first()
                if key:
                    key.api_key = json.dumps(browser_config)
                else:
                    key = ApiKey(provider='browser_config', api_key=json.dumps(browser_config))
                    session.add(key)
                session.commit()
            
            st.success("Configurações do navegador salvas com sucesso!")
        logger.info("Página de configuração carregada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao carregar página de configuração: {e}")
        st.error(f"Erro ao carregar página de configuração: {e}")

def create_task_page():
    """Página para criar novas tarefas"""
    try:
        logger.info("Carregando página de criação de tarefas")
        st.title("🚀 Criar Nova Tarefa")
        
        # Obter chaves do banco de dados
        with get_db_session() as session:
            api_keys = {key.provider: key.api_key for key in session.query(ApiKey).all()}
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            task_instructions = st.text_area(
                "Instruções para o Agente", 
                height=200, 
                placeholder="Digite instruções detalhadas para o agente de IA...\n\nExemplo: Abra https://www.google.com e pesquise por 'Browser Use'"
            )
            
            # Seleção de LLM
            model_col1, model_col2 = st.columns(2)
            
            with model_col1:
                llm_provider = st.selectbox(
                    "Provedor de LLM",
                    options=["openai", "anthropic", "azure", "gemini", "deepseek", "ollama"],
                    index=["openai", "anthropic", "azure", "gemini", "deepseek", "ollama"].index(st.session_state.llm_provider),
                    format_func=lambda x: {
                        'openai': 'OpenAI',
                        'anthropic': 'Anthropic',
                        'azure': 'Azure OpenAI',
                        'gemini': 'Google Gemini',
                        'deepseek': 'DeepSeek',
                        'ollama': 'Ollama (Local)'
                    }.get(x, x)
                )
                st.session_state.llm_provider = llm_provider
            
            with model_col2:
                models = get_llm_models(llm_provider)
                selected_model = st.selectbox(
                    "Modelo",
                    options=models,
                    index=0 if st.session_state.llm_model not in models else models.index(st.session_state.llm_model)
                )
                st.session_state.llm_model = selected_model
            
            # Opções avançadas do navegador
            with st.expander("🔧 Opções avançadas do navegador"):
                col1, col2 = st.columns(2)
                
                with col1:
                    show_browser = st.checkbox(
                        "Mostrar navegador durante execução", 
                        value=st.session_state.browser_config.get('show_browser', True),
                        help="Se marcado, você verá o navegador em tempo real durante a execução da tarefa."
                    )
                    
                    headless = not show_browser  # Inverso do show_browser
                    
                    save_recording = st.checkbox(
                        "Salvar gravação da execução", 
                        value=st.session_state.browser_config.get('save_recording', True),
                        help="Se marcado, uma gravação da execução será salva e poderá ser visualizada depois."
                    )
                
                with col2:
                    max_steps = st.number_input(
                        "Número máximo de passos", 
                        min_value=5, 
                        max_value=50, 
                        value=st.session_state.browser_config.get('max_steps', 15),
                        help="Limita o número máximo de ações que o agente pode executar."
                    )
                    
                    highlight_elements = st.checkbox(
                        "Destacar elementos interativos", 
                        value=st.session_state.browser_config.get('highlight_elements', True),
                        help="Destaca elementos quando o agente interage com eles."
                    )
                
                # Atualizar configuração do navegador
                browser_config = st.session_state.browser_config.copy()
                browser_config.update({
                    'headless': headless,
                    'show_browser': show_browser,
                    'save_recording': save_recording,
                    'max_steps': max_steps,
                    'highlight_elements': highlight_elements,
                    'recording_path': 'static/recordings'
                })
                
                # Atualizar sessão apenas quando necessário
                if browser_config != st.session_state.browser_config:
                    st.session_state.browser_config = browser_config

            # Dados sensíveis
            with st.expander("🔒 Dados Sensíveis"):
                st.markdown("""
                Adicione dados sensíveis que o agente pode precisar usar (como senhas, tokens, etc).
                O agente verá apenas os nomes dos placeholders, não os valores reais.
                """)
                
                # Função para adicionar nova entrada
                def add_sensitive_entry():
                    st.session_state.sensitive_data_entries.append((f"x_data_{len(st.session_state.sensitive_data_entries)+1}", ""))
                
                # Função para remover entrada
                def remove_sensitive_entry(index):
                    st.session_state.sensitive_data_entries.pop(index)
                
                # Mostrar entradas existentes
                for i, (placeholder, value) in enumerate(st.session_state.sensitive_data_entries):
                    col1, col2, col3 = st.columns([2, 3, 1])
                    with col1:
                        new_placeholder = st.text_input(f"Nome do placeholder {i+1}", placeholder, key=f"placeholder_{i}")
                    with col2:
                        new_value = st.text_input(f"Valor sensível {i+1}", value, type="password", key=f"value_{i}")
                    with col3:
                        if st.button("🗑️", key=f"delete_{i}"):
                            remove_sensitive_entry(i)
                            st.experimental_rerun()
                    
                    # Atualizar valores
                    st.session_state.sensitive_data_entries[i] = (new_placeholder, new_value)
                
                # Botão para adicionar nova entrada
                if st.button("➕ Adicionar Dado Sensível"):
                    add_sensitive_entry()
                    st.experimental_rerun()
                
                # Converter entradas para dicionário
                sensitive_data = {
                    placeholder: value 
                    for placeholder, value in st.session_state.sensitive_data_entries 
                    if placeholder and value
                }
                
                # Mostrar como usar na tarefa
                if sensitive_data:
                    st.markdown("### Como usar na tarefa:")
                    examples = []
                    for placeholder in sensitive_data.keys():
                        examples.append(f"- Use **{placeholder}** para o valor sensível (ex: 'Faça login com {placeholder}')")
                    st.markdown("\n".join(examples))
                    
            # Verificar se a chave API está configurada
            api_key = api_keys.get(llm_provider, '')
            azure_endpoint = api_keys.get('azure_endpoint', '')
            
            # Verificar se as chaves necessárias estão configuradas
            api_configured = True
            if llm_provider == 'azure' and (not api_key or not azure_endpoint):
                st.error("Azure OpenAI requer configuração de endpoint e chave API. Configure-os na aba Configuração.")
                api_configured = False
            elif llm_provider != 'ollama' and not api_key:
                st.error(f"Chave API para {llm_provider} não configurada. Configure-a na aba Configuração.")
                api_configured = False
            
            # Botão para iniciar a tarefa
            if st.button("Iniciar Tarefa", type="primary", use_container_width=True, disabled=not api_configured):
                if not task_instructions.strip():
                    st.error("As instruções não podem estar vazias.")
                else:
                    # Gerar ID único para a tarefa
                    task_id = generate_unique_id()
                    
                    # Criar objeto da tarefa no banco de dados
                    with get_db_session() as session:
                        new_task = Task(
                            id=task_id,
                            task=task_instructions,
                            status='created',
                            created_at=datetime.now(),
                            llm_provider=llm_provider,
                            llm_model=selected_model
                        )
                        session.add(new_task)
                        session.commit()
                    
                    st.session_state.current_task = task_id
                    st.success(f"Tarefa criada! ID: {task_id}")
                    
                    # Redirecionar para página de detalhes
                    time.sleep(1)
                    st.experimental_rerun()
        
        with col2:
            # Dicas
            st.markdown("### Dicas")
            st.info(
                "📝 Seja específico nas instruções\n\n"
                "🌐 Inclua URLs completas\n\n"
                "🔍 Descreva cada etapa que deseja que o agente execute"
            )
            
            # Configurações do navegador atual
            st.markdown("### Configuração do Navegador")
            
            # Mostrar configurações atuais
            config_items = [
                f"📐 Dimensões: {st.session_state.browser_config['browser_window_width']}x{st.session_state.browser_config['browser_window_height']}",
                f"👁️ Headless: {'Sim' if st.session_state.browser_config['headless'] else 'Não'}",
                f"🛡️ Segurança desativada: {'Sim' if st.session_state.browser_config['disable_security'] else 'Não'}",
                f"🔆 Destacar elementos: {'Sim' if st.session_state.browser_config['highlight_elements'] else 'Não'}"
            ]
            
            for item in config_items:
                st.markdown(item)
            
            if st.button("Editar Configuração"):
                st.switch_page("app.py")  # Volta para a página de configuração
        logger.info("Página de criação de tarefas carregada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao carregar página de criação de tarefas: {e}")
        st.error(f"Erro ao carregar página de criação de tarefas: {e}")

def task_list_page():
    """Página que lista todas as tarefas com opção de exclusão"""
    try:
        logger.info("Carregando página de lista de tarefas")
        st.title("📋 Minhas Tarefas")
        
        # Verificar se há mensagem de confirmação para exibir
        if 'delete_message' in st.session_state:
            message_type, message = st.session_state.delete_message
            if message_type:
                st.success(message)
            else:
                st.error(message)
            # Limpar a mensagem após exibir
            del st.session_state.delete_message
        
        try:
            # Obter tarefas do banco de dados
            with get_db_session() as session:
                # Converter as tarefas do SQLAlchemy para dicionários enquanto a sessão está aberta
                task_dicts = []
                for task in session.query(Task).order_by(Task.created_at.desc()).all():
                    task_dicts.append({
                        "id": task.id,
                        "task": task.task,
                        "status": task.status,
                        "llm_provider": task.llm_provider,
                        "llm_model": task.llm_model,
                        "created_at": task.created_at,
                        "finished_at": task.finished_at
                    })
            
            # Verificar se existem tarefas
            if not task_dicts:
                st.info("Você ainda não possui tarefas. Crie uma nova na aba 'Criar Tarefa'.")
                return
            
            # Botão para deletar todas as tarefas
            if st.button("🗑️ Deletar Todas as Tarefas", type="secondary"):
                st.session_state.confirm_delete_all = True
                
            # Confirmação para deletar todas
            if st.session_state.get('confirm_delete_all', False):
                st.warning("⚠️ Tem certeza que deseja deletar TODAS as tarefas? Esta ação não pode ser desfeita!")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Sim, deletar tudo"):
                        success_count = 0
                        total_tasks = len(task_dicts)
                        
                        for task in task_dicts:
                            success, _ = delete_task(task["id"])
                            if success:
                                success_count += 1
                        
                        if success_count == total_tasks:
                            st.session_state.delete_message = (True, f"Todas as {total_tasks} tarefas foram deletadas com sucesso!")
                        else:
                            st.session_state.delete_message = (False, f"Foram deletadas {success_count} de {total_tasks} tarefas.")
                        
                        st.session_state.confirm_delete_all = False
                        st.experimental_rerun()
                
                with col2:
                    if st.button("❌ Cancelar"):
                        st.session_state.confirm_delete_all = False
                        st.experimental_rerun()
            
            # Exibir lista de tarefas
            st.write("### Lista de Tarefas")
            
            for i, task in enumerate(task_dicts):
                task_id = task["id"]
                task_desc = task["task"][:50] + "..." if len(task["task"]) > 50 else task["task"]
                task_status = task["status"]
                task_date = format_datetime(task["created_at"])
                
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{i+1}. {task_desc}** (ID: `{task_id}`)")
                    st.write(f"Status: {task_status} | Criado: {task_date}")
                with col2:
                    if st.button(f"👁️ Ver Detalhes", key=f"view_{task_id}"):
                        st.session_state.current_task = task_id
                        st.experimental_rerun()
                with col3:
                    if st.button(f"🗑️ Deletar", key=f"delete_{task_id}"):
                        st.session_state[f"confirm_delete_{task_id}"] = True
                
                # Mostrar confirmação de exclusão se necessário
                if st.session_state.get(f"confirm_delete_{task_id}", False):
                    st.warning(f"⚠️ Tem certeza que deseja deletar esta tarefa? Esta ação não pode ser desfeita!")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button(f"✅ Sim", key=f"confirm_yes_{task_id}"):
                            success, message = delete_task(task_id)
                            st.session_state.delete_message = (success, message)
                            del st.session_state[f"confirm_delete_{task_id}"]
                            st.experimental_rerun()
                    with confirm_col2:
                        if st.button(f"❌ Não", key=f"confirm_no_{task_id}"):
                            del st.session_state[f"confirm_delete_{task_id}"]
                            st.experimental_rerun()
                
                st.markdown("---")
        
        except Exception as e:
            st.error(f"Ocorreu um erro ao carregar as tarefas: {str(e)}")
            st.code(str(e))
        logger.info("Página de lista de tarefas carregada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao carregar página de lista de tarefas: {e}")
        st.error(f"Erro ao carregar página de lista de tarefas: {e}")

def execute_task_thread(task_id):
    """Executa uma tarefa em uma thread separada"""
    logger.info(f"Iniciando thread para executar tarefa {task_id}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(execute_task_async(task_id))
        st.session_state.task_result = result
        logger.info(f"Tarefa {task_id} executada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao executar tarefa {task_id}: {e}")
        st.session_state.task_result = {"error": str(e)}
    finally:
        st.session_state.task_running = False
        loop.close()

async def execute_task_async(task_id):
    """Executa uma tarefa específica assincronamente"""
    logger.info(f"Executando tarefa {task_id} assincronamente")
    
    # Antes de iniciar qualquer coisa, verificar se a tarefa existe e o status atual
    with get_db_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            logger.error(f"Tarefa {task_id} não encontrada")
            return {"error": "Tarefa não encontrada"}
        
        # Se a tarefa já estiver em execução, finalizada ou falha, verificar tempo
        if task.status in ['running', 'finished', 'failed']:
            # Verificar se está em "running" por mais de 30 minutos - provável travamento
            if task.status == 'running' and task.created_at:
                time_diff = datetime.now() - task.created_at
                
                # Se passaram mais de 30 minutos, podemos assumir que houve um problema
                if time_diff.total_seconds() > 1800:  # 30 minutos em segundos
                    logger.warning(f"Tarefa {task_id} está em execução por mais de 30 minutos. Resetando status.")
                    task.status = 'created'  # Reset para permitir nova execução
                    session.commit()
                else:
                    # Está em execução por um tempo razoável, não devemos executar novamente
                    logger.warning(f"Tarefa {task_id} já está em execução.")
                    return {"error": "Tarefa já está em execução"}
            elif task.status in ['finished', 'failed']:
                # Verificar se o usuário quer reexecutar explicitamente
                if not st.session_state.get('force_rerun_task', False):
                    logger.info(f"Tarefa {task_id} já foi executada com status {task.status}.")
                    return {"error": f"Tarefa já foi executada com status {task.status}. Use 'Executar Novamente' para forçar reexecução."}
    
    # Atualizar status para 'running'
    with get_db_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        task.status = 'running'
        session.commit()
    
    # Preparar API Key para o modelo selecionado
    with get_db_session() as session:
        api_keys = {key.provider: key.api_key for key in session.query(ApiKey).all()}
        
    if task.llm_provider == 'azure':
        api_key = api_keys.get('azure', '')
        endpoint = api_keys.get('azure_endpoint', '')
        llm_info = {
            'provider': task.llm_provider,
            'model': task.llm_model,
            'api_key': api_key,
            'endpoint': endpoint
        }
    else:
        api_key = api_keys.get(task.llm_provider, '')
        llm_info = {
            'provider': task.llm_provider,
            'model': task.llm_model,
            'api_key': api_key
        }
    
    # Obter dados sensíveis da sessão
    sensitive_data = {}
    if 'sensitive_data_entries' in st.session_state:
        sensitive_data = {
            placeholder: value 
            for placeholder, value in st.session_state.sensitive_data_entries 
            if placeholder and value
        }
    
    try:
        logger.info(f"Executando agente para tarefa {task_id}")
        # Executar o agente
        result = await run_agent_task(
            task_id=task_id,
            task_instructions=task.task,
            llm=llm_info,
            browser_config=st.session_state.browser_config,
            sensitive_data=sensitive_data
        )
        
        # Atualizar o status da tarefa no banco de dados
        with get_db_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                logger.error(f"Tarefa {task_id} não encontrada após execução")
                return {"error": "Tarefa não encontrada após execução"}
                
            # Definir status correto
            task.status = result.get('status', 'unknown')
            if task.status not in ['created', 'running', 'finished', 'failed']:
                task.status = 'finished' if not result.get('errors') else 'failed'
                
            task.finished_at = datetime.now()
            task.output = result.get('output', '')
            
            # Criar ou atualizar o histórico da tarefa
            task_history = session.query(TaskHistory).filter(TaskHistory.task_id == task_id).first()
            
            if task_history:
                task_history.steps = json.dumps(result.get('steps', []))
                task_history.urls = json.dumps(result.get('urls', []))
                task_history.screenshots = json.dumps(result.get('screenshots', []))
                task_history.errors = json.dumps(result.get('errors', []))
            else:
                task_history = TaskHistory(
                    task_id=task_id,
                    steps=json.dumps(result.get('steps', [])),
                    urls=json.dumps(result.get('urls', [])),
                    screenshots=json.dumps(result.get('screenshots', [])),
                    errors=json.dumps(result.get('errors', []))
                )
                session.add(task_history)
            
            # Calcular duração total
            if task.created_at and task.finished_at:
                duration_seconds = (task.finished_at - task.created_at).total_seconds()
                task_history.duration = str(int(duration_seconds))
            
            session.commit()
        
        # Limpar flag de reexecução forçada se existir
        if 'force_rerun_task' in st.session_state:
            del st.session_state['force_rerun_task']
        
        logger.info(f"Tarefa {task_id} concluída com status: {result.get('status', 'unknown')}")
        return result
        
    except Exception as e:
        logger.error(f"Erro durante execução da tarefa {task_id}: {str(e)}")
        
        # Atualizar status para falha em caso de exceção
        with get_db_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = 'failed'
                task.finished_at = datetime.now()
                task.output = f"Erro na execução: {str(e)}"
                session.commit()
        
        return {
            "status": "failed",
            "error": str(e),
            "errors": [str(e)]
        }

def task_detail_page():
    """Página de detalhes da tarefa atual"""
    try:
        logger.info("Carregando página de detalhes da tarefa")
        if not st.session_state.current_task:
            st.error("Nenhuma tarefa selecionada.")
            return
        
        task_id = st.session_state.current_task
        
        # Obter tarefa e histórico do banco de dados
        with get_db_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                st.error(f"Tarefa {task_id} não encontrada.")
                if st.button("Voltar à lista de tarefas"):
                    st.session_state.current_task = None
                    st.experimental_rerun()
                return
            
            # Armazenar os atributos que precisamos enquanto a sessão está aberta
            task_data = {
                'id': task.id,
                'status': task.status,
                'created_at': task.created_at,
                'finished_at': task.finished_at,
                'llm_provider': task.llm_provider,
                'llm_model': task.llm_model,
                'task': task.task,
                'output': task.output
            }
            
            # Obter o histórico da tarefa
            task_history = session.query(TaskHistory).filter(TaskHistory.task_id == task_id).first()
            history_data = None
            if task_history:
                history_data = {
                    'steps': task_history.steps,
                    'urls': task_history.urls,
                    'screenshots': task_history.screenshots,
                    'errors': task_history.errors
                }
        
        # Exibir cabeçalho
        status = task_data['status']
        status_color = get_status_color(status)
        
        st.title(f"📊 Detalhes da Tarefa")
        st.markdown(f"**ID da Tarefa:** `{task_id}`")
        
        # Barra de status e controles
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown(f"**Status:** <span style='color:{status_color};font-weight:bold;'>{status.upper()}</span>", unsafe_allow_html=True)
        
        # Controles conforme o status
        with col2:
            if status == 'running':
                st.info("Tarefa em execução. Aguarde a conclusão ou atualize a página para ver o progresso.")
                if st.button("🔄 Atualizar Status", key="refresh_status"):
                    st.experimental_rerun()
            elif status == 'created':
                run_col1, run_col2 = st.columns(2)
                with run_col1:
                    if st.button("▶️ Executar Tarefa", key="run_task", use_container_width=True):
                        if not st.session_state.task_running:
                            st.session_state.task_running = True
                            logger.info(f"Iniciando execução da tarefa {task_id}")
                            # Iniciar thread para executar a tarefa
                            thread = threading.Thread(target=execute_task_thread, args=(task_id,))
                            thread.daemon = True
                            thread.start()
                            st.info("Iniciando execução da tarefa...")
                            st.experimental_rerun()
                with run_col2:
                    headless = st.checkbox("Executar em modo headless", value=st.session_state.browser_config.get('headless', False),
                                    help="Se marcado, o navegador não será visível durante a execução")
                    if headless != st.session_state.browser_config.get('headless', False):
                        # Atualizar configuração
                        browser_config = st.session_state.browser_config.copy()
                        browser_config['headless'] = headless
                        browser_config['show_browser'] = not headless
                        st.session_state.browser_config = browser_config
            elif status in ['finished', 'failed']:
                if st.button("🔄 Executar Novamente", key="rerun_task", use_container_width=True):
                    st.session_state['force_rerun_task'] = True
                    if not st.session_state.task_running:
                        st.session_state.task_running = True
                        logger.info(f"Reexecutando tarefa {task_id}")
                        # Iniciar thread para executar a tarefa
                        thread = threading.Thread(target=execute_task_thread, args=(task_id,))
                        thread.daemon = True
                        thread.start()
                        st.info("Reiniciando execução da tarefa...")
                        st.experimental_rerun()
        
        # Detalhes da tarefa
        st.markdown("### Informações da Tarefa")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Criada em:** {format_datetime(task_data['created_at'])}")
            if task_data['finished_at']:
                st.markdown(f"**Concluída em:** {format_datetime(task_data['finished_at'])}")
            st.markdown(f"**Modelo:** {task_data['llm_provider']} / {task_data['llm_model']}")
        
        # Instruções
        st.markdown("### Instruções")
        st.code(task_data['task'])
        
        # Se a tarefa estiver em execução, mostrar informações de progresso
        if st.session_state.task_running:
            st.info("A tarefa está sendo executada em segundo plano... Isso pode levar alguns minutos.")
            progress_placeholder = st.empty()
            
            # Verificar estado atual
            with get_db_session() as session:
                current_task = session.query(Task).filter(Task.id == task_id).first()
                current_status = current_task.status if current_task else "unknown"
                
                # Verificar histórico para obter informações atuais
                task_history = session.query(TaskHistory).filter(TaskHistory.task_id == task_id).first()
                if task_history:
                    steps = json.loads(task_history.steps) if task_history.steps else []
                    urls = json.loads(task_history.urls) if task_history.urls else []
                    screenshots = json.loads(task_history.screenshots) if task_history.screenshots else []
                    
                    # Mostrar progresso atual
                    with progress_placeholder.container():
                        st.write(f"Status atual: **{current_status}**")
                        st.write(f"Passos executados: **{len(steps)}**")
                        st.write(f"URLs visitadas: **{len(urls)}**")
                        
                        # Mostrar último screenshot se disponível
                        if screenshots:
                            last_screenshot = screenshots[-1]
                            if os.path.exists(last_screenshot):
                                st.image(last_screenshot, caption="Última captura de tela")
            
            if st.button("Atualizar Progresso"):
                st.experimental_rerun()
        
        # Se o resultado da tarefa estiver disponível na sessão, exibi-lo
        if st.session_state.task_result and not st.session_state.task_running:
            st.success("Tarefa concluída!")
            # Limpar resultado após exibir
            st.session_state.task_result = None
            # Recarregar a página para mostrar os dados atualizados do banco
            st.experimental_rerun()
        
        # Se o status for 'created' e a tarefa não estiver em execução, propor execução
        if status == 'created' and not st.session_state.task_running:
            st.info("Esta tarefa está aguardando execução. Clique em 'Executar Tarefa' para iniciá-la.")
        
        # Verificar se há gravação para esta tarefa
        recording_path = os.path.join(st.session_state.browser_config.get('recording_path', 'static/recordings'), f"{task_id}.webm")
        if os.path.exists(recording_path):
            st.markdown("### 🎬 Gravação da Execução")
            st.video(recording_path)
        
        # Exibir resultados se a tarefa estiver concluída e houver dados no histórico
        if history_data and status in ['finished', 'failed']:
            # Desserializar os dados do histórico
            steps = json.loads(history_data['steps']) if history_data['steps'] else []
            urls = json.loads(history_data['urls']) if history_data['urls'] else []
            screenshots = json.loads(history_data['screenshots']) if history_data['screenshots'] else []
            errors = json.loads(history_data['errors']) if history_data['errors'] else []
            
            # Mostrar passos da execução
            if steps:
                st.markdown("### Passos da Execução")
                
                for i, step in enumerate(steps):
                    with st.expander(f"Passo {step.get('step', i+1)}"):
                        if 'evaluation_previous_goal' in step and step['evaluation_previous_goal']:
                            st.markdown("**Pensamento:**")
                            st.info(step['evaluation_previous_goal'])
                        
                        if 'next_goal' in step and step['next_goal']:
                            st.markdown("**Ação:**")
                            st.success(step['next_goal'])
            
            # Mostrar URLs visitadas
            if urls:
                st.markdown("### URLs Visitadas")
                for url in urls:
                    st.markdown(f"- {url}")
            
            # Mostrar screenshots se disponíveis e não existir gravação
            if screenshots and not os.path.exists(recording_path):
                st.markdown("### 📸 Capturas de Tela")
                
                # Exibir slideshow com os screenshots
                screenshot_index = st.session_state.get('screenshot_index', 0)
                total_screenshots = len(screenshots)
                
                if total_screenshots > 0:
                    # Navegação do slideshow
                    col1, col2, col3 = st.columns([1, 10, 1])
                    
                    with col1:
                        if st.button("◀️", key="prev_screenshot", disabled=screenshot_index <= 0):
                            st.session_state.screenshot_index = max(0, screenshot_index - 1)
                            st.experimental_rerun()
                    
                    with col2:
                        # Exibir screenshot atual
                        if 0 <= screenshot_index < total_screenshots:
                            current_screenshot = screenshots[screenshot_index]
                            if os.path.exists(current_screenshot):
                                st.image(current_screenshot, caption=f"Captura {screenshot_index + 1} de {total_screenshots}")
                            else:
                                st.warning(f"Imagem não encontrada: {current_screenshot}")
                    
                    with col3:
                        if st.button("▶️", key="next_screenshot", disabled=screenshot_index >= total_screenshots - 1):
                            st.session_state.screenshot_index = min(total_screenshots - 1, screenshot_index + 1)
                            st.experimental_rerun()
            
            # Mostrar resultado final
            if task_data['output']:
                st.markdown("### Resultado Final")
                st.code(task_data['output'])
            
            # Mostrar erros se houver
            if errors:
                st.markdown("### Erros")
                for error in errors:
                    st.error(error)
        
        # Botão para voltar à lista
        if st.button("← Voltar à lista de tarefas", key="back_to_list"):
            st.session_state.current_task = None
            st.experimental_rerun()
        logger.info("Página de detalhes da tarefa carregada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao carregar página de detalhes da tarefa: {e}")
        st.error(f"Erro ao carregar página de detalhes da tarefa: {e}")

def main():
    """Função principal"""
    try:
        logger.info("Iniciando função principal")
        # Inicializar banco de dados se necessário
        if not st.session_state.get('db_initialized', False):
            try:
                logger.info("Inicializando banco de dados...")
                init_db()
                logger.info("Banco de dados inicializado com sucesso")
                
                # Carregar configurações do navegador do banco de dados
                with get_db_session() as session:
                    browser_config = session.query(ApiKey).filter(ApiKey.provider == 'browser_config').first()
                    if browser_config and browser_config.api_key:
                        try:
                            st.session_state.browser_config = json.loads(browser_config.api_key)
                            logger.info("Configurações do navegador carregadas do banco de dados")
                        except Exception as e:
                            logger.error(f"Erro ao carregar configurações do navegador: {e}")
                
                st.session_state.db_initialized = True
                logger.info("Inicialização concluída")
            except Exception as e:
                logger.error(f"Erro ao inicializar banco de dados: {e}")
        
        # Inicializar estado da sessão
        init_session_state()
        
        # Sidebar - versão mais simples para evitar problemas de renderização
        with st.sidebar:
            st.title("🤖 Gerenciador de Agentes IA")
            
            # Menu simplificado
            nav_options = ["Configuração", "Criar Tarefa", "Minhas Tarefas"]
            if st.session_state.current_task:
                nav_options.append("Detalhes da Tarefa")
                
            nav_option = st.radio(
                "Navegação",
                options=nav_options,
                index=0
            )
        
        # Conteúdo principal
        if nav_option == "Configuração":
            auth_page()
        elif nav_option == "Detalhes da Tarefa" and st.session_state.current_task:
            task_detail_page()
        elif nav_option == "Minhas Tarefas":
            task_list_page()
        else:
            create_task_page()
        
        logger.info("Função principal executada com sucesso")
    except Exception as e:
        logger.error(f"Erro na função principal: {e}")
        st.error(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    try:
        logger.info("Iniciando a aplicação")
        main()
        logger.info("Aplicação iniciada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao iniciar a aplicação: {e}")