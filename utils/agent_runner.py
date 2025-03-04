import asyncio
import json
import logging
import os
import time
import glob
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import tempfile

# Importações internas
from db.database import get_db_session
from db.models import Task, TaskHistory
from utils.helpers import save_screenshot
from utils.sensitive_data import sensitive_data_manager
from utils.controller import controller

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Implementação do LLM para diferentes provedores
async def call_llm(provider, model, api_key, prompt, endpoint=None, image_data=None, use_vision=True):
    """Função para chamar diferentes provedores de LLM com suporte a visão."""
    try:
        messages = [{"role": "user", "content": prompt}]

        # Adicionar dados de imagem se fornecidos e use_vision estiver ativado
        if image_data and use_vision:
            # Implementar lógica específica para cada provedor que suporta visão
            if provider == 'openai':
                messages = [
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                    ]}
                ]
        
        if provider == 'openai':
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            return response.choices[0].message.content
        
        elif provider == 'anthropic':
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            
            # Anthropic suporta imagens de maneira diferente
            if image_data and use_vision:
                messages = [
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}}
                        ]
                    }
                ]
            
            response = client.messages.create(
                model=model,
                max_tokens=1500,
                temperature=0.7,
                messages=messages
            )
            return response.content[0].text
        
        elif provider == 'azure':
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=api_key,
                api_version="2023-05-15",
                azure_endpoint=endpoint
            )
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            return response.choices[0].message.content
        
        elif provider == 'gemini':
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model_obj = genai.GenerativeModel(model)
            
            # Gemini suporta imagens de forma diferente
            if image_data and use_vision:
                import base64
                from PIL import Image
                import io
                
                # Converter base64 para imagem
                img_data = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(img_data))
                
                # Criar geração com imagem
                response = model_obj.generate_content([prompt, image])
            else:
                response = model_obj.generate_content(prompt)
                
            return response.text
        
        elif provider == 'deepseek':
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            return response.choices[0].message.content
        
        elif provider == 'ollama':
            import requests
            
            # Ollama não suporta imagens na API padrão
            payload = {
                'model': model,
                'prompt': prompt,
                'stream': False
            }
            
            response = requests.post(
                'http://localhost:11434/api/generate',
                json=payload
            )
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                raise Exception(f"Erro no Ollama: {response.text}")
        
        else:
            raise ValueError(f"Provedor LLM não suportado: {provider}")
    
    except Exception as e:
        logger.error(f"Erro ao chamar LLM {provider}/{model}: {str(e)}")
        return f"Erro ao gerar resposta: {str(e)}"

# Sistema de prompt do agente (expandido com base na documentação do Browser-use)
AGENT_SYSTEM_PROMPT = """
Você é um agente de IA designado para ajudar com tarefas de navegação web. Você usará o navegador para completar tarefas conforme instruções. Siga estas diretrizes:

1. Planeje cuidadosamente cada etapa antes de executá-la.
2. Use o navegador para interagir com sites e aplicativos web.
3. Quando necessário, capture screenshots para documentar seu progresso.
4. Ao final, forneça um resumo claro do que foi realizado.

Você pode executar as seguintes ações:
- navigate(url): Navegar para uma URL específica
- click(selector): Clicar em um elemento na página
- type(selector, text): Digitar texto em um campo
- screenshot(): Capturar screenshot da página atual
- extract_text(selector): Extrair texto de um elemento
- wait(seconds): Esperar um número específico de segundos
- scroll_down(amount): Rolar a página para baixo
- scroll_up(amount): Rolar a página para cima
- search_google(query): Pesquisar no Google
- open_tab(url): Abrir uma nova aba com URL
- switch_tab(index): Alternar para outra aba
- close_tab(): Fechar a aba atual
- extract_all_links(): Extrair todos os links da página
- extract_all_text(): Extrair todo o texto da página
- upload_file(selector, file_path): Fazer upload de arquivo

Funções personalizadas disponíveis:
- debug_message(message): Exibe uma mensagem de depuração no console
- ask_human(question): Pergunta ao usuário e retorna a resposta
- upload_file(selector, file_path): Faz upload de um arquivo para um elemento na página
- notify_user(message, type): Exibe uma notificação para o usuário
- save_to_file(content, filename): Salva conteúdo em um arquivo
- extract_tables(): Extrai tabelas da página atual

Analise a tarefa, divida-a em etapas lógicas e execute-as sequencialmente. Se encontrar um obstáculo, tente contorná-lo ou explique por que não é possível continuar.

INSTRUÇÕES PARA A TAREFA:
"""

# Modelos Pydantic para configurações avançadas
class BrowserContextConfig(BaseModel):
    """Configuração avançada para o contexto do navegador"""
    cookies_file: Optional[str] = None
    wait_for_network_idle_page_load_time: float = 3.0
    minimum_wait_page_load_time: float = 0.5
    maximum_wait_page_load_time: float = 5.0
    browser_window_size: Dict[str, int] = Field(default_factory=lambda: {"width": 1280, "height": 1100})
    locale: Optional[str] = None
    user_agent: Optional[str] = None
    highlight_elements: bool = True
    viewport_expansion: int = 500
    allowed_domains: Optional[List[str]] = None
    save_recording_path: Optional[str] = None
    trace_path: Optional[str] = None

class ActionResult(BaseModel):
    """Modelo para resultado de ações"""
    success: bool = True
    extracted_content: Optional[str] = None
    error: Optional[str] = None

async def run_agent_task(task_id: str, task_instructions: str, llm: Dict, browser_config: Dict, sensitive_data: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Executa uma tarefa de agente usando LLM e Playwright"""
    logger.info(f"Iniciando tarefa {task_id}")
    
    # Importar Playwright apenas quando necessário
    from playwright.async_api import async_playwright
    
    result = {
        'status': 'running',
        'steps': [],
        'urls': [],
        'screenshots': [],
        'errors': [],
        'output': '',
        'sensitive_data': {}  # Para armazenar dados sensíveis
    }
    
    # Processar dados sensíveis
    if sensitive_data:
        # Adicionar dados sensíveis ao gerenciador
        sensitive_data_manager.add_sensitive_data(sensitive_data)
        
        # Mascarar a tarefa para proteger dados sensíveis
        task_instructions = sensitive_data_manager.mask_prompt(task_instructions)
        
        # Adicionar instruções sobre dados sensíveis ao prompt
        task_instructions += f"\n\n{sensitive_data_manager.get_placeholder_description()}"
    
    # Diretório temporário para arquivos
    temp_dir = tempfile.mkdtemp()
    logger.info(f"Diretório temporário criado: {temp_dir}")
    
    # Diretório para gravações
    if browser_config.get('save_recording', False):
        recording_path = browser_config.get('recording_path', 'static/recordings')
        os.makedirs(recording_path, exist_ok=True)
        recording_file = os.path.join(recording_path, f"{task_id}.webm")
    else:
        recording_file = None
    
    try:
        # Iniciar o Playwright
        async with async_playwright() as p:
            # Configuração avançada do navegador
            browser_context_config = BrowserContextConfig(
                browser_window_size={"width": browser_config.get('browser_window_width', 1280), 
                                    "height": browser_config.get('browser_window_height', 1100)},
                highlight_elements=browser_config.get('highlight_elements', True),
                wait_for_network_idle_page_load_time=browser_config.get('wait_for_network_idle', 3.0)
            )
            
            # Configurar o navegador
            launch_options = {
                'headless': browser_config.get('headless', True),
                'args': []
            }
            
            # Adicionar argumentos para desativar segurança se configurado
            if browser_config.get('disable_security', False):
                launch_options['args'].extend([
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ])
            
            # Usar caminho específico do Chrome se configurado (Permite conectar a um Chrome existente)
            chrome_path = browser_config.get('chrome_instance_path')
            if chrome_path and os.path.exists(chrome_path):
                launch_options['executable_path'] = chrome_path
                logger.info(f"Usando Chrome em: {chrome_path}")
            
            # Iniciar navegador
            browser = await p.chromium.launch(**launch_options)
            
            # Configurar contexto com opções avançadas
            context_options = {
                'viewport': browser_context_config.browser_window_size,
            }
            
            # Adicionar locale se configurado
            if browser_context_config.locale:
                context_options['locale'] = browser_context_config.locale
                
            # Adicionar user agent se configurado
            if browser_context_config.user_agent:
                context_options['user_agent'] = browser_context_config.user_agent
                
            # Adicionar gravação se configurado
            if recording_file:
                context_options['record_video_dir'] = os.path.dirname(recording_file)
                context_options['record_video_size'] = browser_context_config.browser_window_size
                logger.info(f"Gravando vídeo em: {recording_file}")
                
            # Criar contexto e página
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            
            # Lista para manter controle de abas abertas
            tabs = [page]
            current_tab_index = 0
            
            # Funções de ação avançadas do navegador
            async def navigate(url: str) -> ActionResult:
                try:
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    
                    # Verificar domínios permitidos
                    if browser_context_config.allowed_domains:
                        domain = url.split('//')[-1].split('/')[0]
                        base_domain = '.'.join(domain.split('.')[-2:]) if len(domain.split('.')) > 1 else domain
                        
                        if not any(base_domain.endswith(allowed) for allowed in browser_context_config.allowed_domains):
                            return ActionResult(
                                success=False,
                                error=f"Domínio não permitido: {base_domain}. Permitidos: {browser_context_config.allowed_domains}"
                            )
                    
                    # Navegação com espera configurável
                    response = await tabs[current_tab_index].goto(
                        url, 
                        wait_until='domcontentloaded',
                        timeout=browser_context_config.maximum_wait_page_load_time * 1000
                    )
                    
                    # Esperar pelo tempo mínimo configurado
                    await asyncio.sleep(browser_context_config.minimum_wait_page_load_time)
                    
                    # Esperar pela rede ficar ociosa
                    if browser_context_config.wait_for_network_idle_page_load_time > 0:
                        try:
                            await tabs[current_tab_index].wait_for_load_state('networkidle', 
                                timeout=browser_context_config.wait_for_network_idle_page_load_time * 1000)
                        except Exception as e:
                            logger.warning(f"Tempo esgotado esperando rede ficar ociosa: {str(e)}")
                    
                    result['urls'].append(url)
                    return ActionResult(
                        success=True,
                        extracted_content=f"Navegou para {url}. Status: {response.status if response else 'desconhecido'}"
                    )
                except Exception as e:
                    error_msg = f"Erro ao navegar para {url}: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            async def click(selector: str) -> ActionResult:
                try:
                    current_page = tabs[current_tab_index]
                    
                    # Destacar elemento se configurado
                    if browser_context_config.highlight_elements:
                        await current_page.evaluate(f"""(selector) => {{
                            const el = document.querySelector(selector);
                            if (el) {{
                                const originalStyle = el.getAttribute('style') || '';
                                el.setAttribute('style', originalStyle + '; border: 3px solid red; background-color: rgba(255, 0, 0, 0.2);');
                                setTimeout(() => el.setAttribute('style', originalStyle), 2000);
                            }}
                        }}""", selector)
                        
                        # Pequena pausa para visualização
                        await asyncio.sleep(0.5)
                    
                    await current_page.click(selector)
                    
                    # Esperar um pouco para a ação ter efeito
                    await asyncio.sleep(browser_context_config.minimum_wait_page_load_time)
                    
                    return ActionResult(
                        success=True,
                        extracted_content=f"Clicou em {selector}"
                    )
                except Exception as e:
                    error_msg = f"Erro ao clicar em {selector}: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            async def type_text(selector: str, text: str) -> ActionResult:
                try:
                    current_page = tabs[current_tab_index]
                    
                    # Verificar se o texto contém dados sensíveis
                    sensitive_text = text
                    if sensitive_data:
                        # Desmascarar o texto (substituir placeholders por valores reais)
                        for placeholder, value in sensitive_data.items():
                            placeholder_pattern = f"[{placeholder}]"
                            if placeholder_pattern in text:
                                sensitive_text = text.replace(placeholder_pattern, value)
                            elif placeholder == text:
                                sensitive_text = value
                    
                    # Destacar elemento se configurado
                    if browser_context_config.highlight_elements:
                        await current_page.evaluate(f"""(selector) => {{
                            const el = document.querySelector(selector);
                            if (el) {{
                                const originalStyle = el.getAttribute('style') || '';
                                el.setAttribute('style', originalStyle + '; border: 3px solid blue; background-color: rgba(0, 0, 255, 0.2);');
                                setTimeout(() => el.setAttribute('style', originalStyle), 2000);
                            }}
                        }}""", selector)
                        
                        # Pequena pausa para visualização
                        await asyncio.sleep(0.5)
                    
                    # Usar o texto original (possivelmente com dados sensíveis) para digitar
                    await current_page.fill(selector, sensitive_text)
                    
                    # Retornar o texto mascarado para o log
                    masked_text = text
                    if sensitive_data:
                        # Remover valores sensíveis do log
                        for placeholder, value in sensitive_data.items():
                            if value in text:
                                masked_text = text.replace(value, f"[{placeholder}]")
                    
                    return ActionResult(
                        success=True,
                        extracted_content=f"Digitou '{masked_text}' em {selector}"  # Texto com placeholders
                    )
                except Exception as e:
                    error_msg = f"Erro ao digitar em {selector}: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            async def take_screenshot() -> ActionResult:
                try:
                    current_page = tabs[current_tab_index]
                    screenshot_bytes = await current_page.screenshot(
                        full_page=browser_config.get('full_page_screenshot', False)
                    )
                    filepath = save_screenshot(screenshot_bytes, task_id)
                    result['screenshots'].append(filepath)
                    
                    return ActionResult(
                        success=True,
                        extracted_content=f"Screenshot capturado: {filepath}"
                    )
                except Exception as e:
                    error_msg = f"Erro ao capturar screenshot: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            async def extract_text(selector: str) -> ActionResult:
                try:
                    current_page = tabs[current_tab_index]
                    
                    # Destacar elemento se configurado
                    if browser_context_config.highlight_elements:
                        await current_page.evaluate(f"""(selector) => {{
                            const el = document.querySelector(selector);
                            if (el) {{
                                const originalStyle = el.getAttribute('style') || '';
                                el.setAttribute('style', originalStyle + '; border: 3px solid green; background-color: rgba(0, 255, 0, 0.2);');
                                setTimeout(() => el.setAttribute('style', originalStyle), 2000);
                            }}
                        }}""", selector)
                    
                    text = await current_page.text_content(selector)
                    
                    # Filtrar dados sensíveis
                    if sensitive_data:
                        for placeholder, value in sensitive_data.items():
                            if value in text:
                                text = text.replace(value, f"[{placeholder}]")
                    
                    return ActionResult(
                        success=True,
                        extracted_content=f"Texto extraído de {selector}: {text}"
                    )
                except Exception as e:
                    error_msg = f"Erro ao extrair texto de {selector}: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            async def wait(seconds: int) -> ActionResult:
                try:
                    # Limitar o tempo máximo de espera
                    seconds = min(seconds, 30)  # Máximo de 30 segundos
                    await asyncio.sleep(seconds)
                    return ActionResult(
                        success=True,
                        extracted_content=f"Esperou {seconds} segundos"
                    )
                except Exception as e:
                    error_msg = f"Erro ao esperar: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            # Funções adicionais baseadas na documentação do Browser-use
            async def scroll_down(amount: int = 500) -> ActionResult:
                try:
                    current_page = tabs[current_tab_index]
                    await current_page.evaluate(f"window.scrollBy(0, {amount})")
                    return ActionResult(
                        success=True,
                        extracted_content=f"Rolou {amount} pixels para baixo"
                    )
                except Exception as e:
                    error_msg = f"Erro ao rolar para baixo: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            async def scroll_up(amount: int = 500) -> ActionResult:
                try:
                    current_page = tabs[current_tab_index]
                    await current_page.evaluate(f"window.scrollBy(0, -{amount})")
                    return ActionResult(
                        success=True,
                        extracted_content=f"Rolou {amount} pixels para cima"
                    )
                except Exception as e:
                    error_msg = f"Erro ao rolar para cima: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            async def search_google(query: str) -> ActionResult:
                try:
                    # Navegar para o Google
                    google_result = await navigate("https://www.google.com")
                    if not google_result.success:
                        return google_result
                    
                    # Digitar consulta no campo de pesquisa
                    current_page = tabs[current_tab_index]
                    await current_page.fill('input[name="q"]', query)
                    await current_page.press('input[name="q"]', 'Enter')
                    
                    # Esperar pelos resultados
                    await current_page.wait_for_load_state('networkidle')
                    
                    return ActionResult(
                        success=True,
                        extracted_content=f"Pesquisou por '{query}' no Google"
                    )
                except Exception as e:
                    error_msg = f"Erro ao pesquisar no Google: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            async def open_tab(url: str = None) -> ActionResult:
                try:
                    # Criar nova página
                    new_page = await context.new_page()
                    tabs.append(new_page)
                    nonlocal current_tab_index
                    current_tab_index = len(tabs) - 1
                    
                    # Navegar para URL se fornecida
                    if url:
                        nav_result = await navigate(url)
                        return ActionResult(
                            success=nav_result.success,
                            extracted_content=f"Nova aba criada e navegada para {url}",
                            error=nav_result.error
                        )
                    
                    return ActionResult(
                        success=True,
                        extracted_content=f"Nova aba criada (índice {current_tab_index})"
                    )
                except Exception as e:
                    error_msg = f"Erro ao abrir nova aba: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            async def switch_tab(index: int) -> ActionResult:
                try:
                    if 0 <= index < len(tabs):
                        nonlocal current_tab_index
                        current_tab_index = index
                        return ActionResult(
                            success=True,
                            extracted_content=f"Alternado para aba {index}"
                        )
                    else:
                        error_msg = f"Índice de aba inválido: {index}. Disponíveis: 0-{len(tabs)-1}"
                        return ActionResult(success=False, error=error_msg)
                except Exception as e:
                    error_msg = f"Erro ao alternar abas: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            async def close_tab() -> ActionResult:
                try:
                    nonlocal current_tab_index
                    if len(tabs) <= 1:
                        return ActionResult(
                            success=False,
                            error="Não é possível fechar a última aba"
                        )
                    
                    # Fechar a aba atual
                    await tabs[current_tab_index].close()
                    tabs.pop(current_tab_index)
                    
                    # Ajustar o índice atual
                    current_tab_index = max(0, current_tab_index - 1)
                    
                    return ActionResult(
                        success=True,
                        extracted_content=f"Aba fechada. Agora na aba {current_tab_index}"
                    )
                except Exception as e:
                    error_msg = f"Erro ao fechar aba: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
                
            async def extract_all_links() -> ActionResult:
                try:
                    current_page = tabs[current_tab_index]
                    links = await current_page.evaluate("""() => {
                        return Array.from(document.querySelectorAll('a[href]'))
                            .map(a => ({
                                text: a.innerText.trim(),
                                href: a.href,
                                visible: a.offsetParent !== null
                            }))
                            .filter(link => link.text && link.href);
                    }""")
                    
                    # Formatar os links para exibição
                    formatted_links = []
                    for i, link in enumerate(links[:30]):  # Limitar a 30 links
                        formatted_links.append(f"{i+1}. '{link['text']}' - {link['href']}")
                    
                    all_links = "\n".join(formatted_links)
                    if len(links) > 30:
                        all_links += f"\n... e mais {len(links) - 30} links (mostrando apenas os primeiros 30)"
                    
                    return ActionResult(
                        success=True,
                        extracted_content=f"Links encontrados na página:\n{all_links}"
                    )
                except Exception as e:
                    error_msg = f"Erro ao extrair links: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
                
            async def extract_all_text() -> ActionResult:
                try:
                    current_page = tabs[current_tab_index]
                    text = await current_page.evaluate("""() => {
                        return document.body.innerText;
                    }""")
                    
                    # Limitar o texto para não sobrecarregar o LLM
                    max_chars = 4000
                    if len(text) > max_chars:
                        text = text[:max_chars] + f"\n... (texto truncado, mostrando {max_chars} de {len(text)} caracteres)"
                    
                    # Filtrar dados sensíveis
                    if sensitive_data:
                        text = sensitive_data_manager.filter_page_content(text)
                    
                    return ActionResult(
                        success=True,
                        extracted_content=f"Texto da página:\n{text}"
                    )
                except Exception as e:
                    error_msg = f"Erro ao extrair texto: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
                
            async def upload_file(selector: str, filename: str) -> ActionResult:
                try:
                    current_page = tabs[current_tab_index]
                    
                    # Criar arquivo temporário com nome específico para upload
                    temp_file_path = os.path.join(temp_dir, filename)
                    with open(temp_file_path, 'w') as f:
                        f.write(f"Arquivo temporário para upload: {filename}")
                    
                    # Destacar elemento se configurado
                    if browser_context_config.highlight_elements:
                        await current_page.evaluate(f"""(selector) => {{
                            const el = document.querySelector(selector);
                            if (el) {{
                                const originalStyle = el.getAttribute('style') || '';
                                el.setAttribute('style', originalStyle + '; border: 3px solid purple; background-color: rgba(128, 0, 128, 0.2);');
                                setTimeout(() => el.setAttribute('style', originalStyle), 2000);
                            }}
                        }}""", selector)
                    
                    # Fazer upload do arquivo
                    await current_page.set_input_files(selector, temp_file_path)
                    
                    return ActionResult(
                        success=True,
                        extracted_content=f"Arquivo '{filename}' enviado através do elemento {selector}"
                    )
                except Exception as e:
                    error_msg = f"Erro ao fazer upload de arquivo: {str(e)}"
                    result['errors'].append(error_msg)
                    return ActionResult(success=False, error=error_msg)
            
            # Mapeamento de nomes de ações para funções
            action_map = {
                'navigate': navigate,
                'click': click,
                'type': type_text,
                'type_text': type_text,
                'screenshot': take_screenshot,
                'extract_text': extract_text,
                'wait': wait,
                'scroll_down': scroll_down,
                'scroll_up': scroll_up,
                'search_google': search_google,
                'open_tab': open_tab,
                'switch_tab': switch_tab,
                'close_tab': close_tab,
                'extract_all_links': extract_all_links,
                'extract_all_text': extract_all_text,
                'upload_file': upload_file
            }
            
            # Prompt inicial para o agente
            prompt = AGENT_SYSTEM_PROMPT + task_instructions
            
            # Adicionar sistema de processamento de formato de saída personalizado
            output_format = browser_config.get('output_format')
            if output_format:
                prompt += f"\n\nIMPORTANTE: Você deve retornar o resultado final no seguinte formato JSON:\n{output_format}"
            
            # Verificar se há ações iniciais para executar
            initial_actions = browser_config.get('initial_actions', [])
            if initial_actions:
                prompt += "\n\nAções iniciais executadas automaticamente:"
                
                for action_dict in initial_actions:
                    for action_name, params in action_dict.items():
                        action_func = action_map.get(action_name)
                        if action_func:
                            if isinstance(params, dict):
                                action_result = await action_func(**params)
                            else:
                                action_result = await action_func(params)
                            
                            prompt += f"\n- {action_name}({params}): {action_result.extracted_content}"
            
            # Configuração para uso de visão
            use_vision = browser_config.get('use_vision', True)
            
            # Executar passos do agente em loop
            step_count = 0
            max_steps = browser_config.get('max_steps', 15)  # Configurável
            
            while step_count < max_steps:
                step_count += 1
                
                try:
                    # Capturar screenshot da página atual para visão, se habilitado
                    page_image_base64 = None
                    if use_vision:
                        current_page = tabs[current_tab_index]
                        screenshot = await current_page.screenshot()
                        import base64
                        page_image_base64 = base64.b64encode(screenshot).decode('utf-8')
                    
                    # Chamar o LLM para obter próxima ação
                    llm_response = await call_llm(
                        provider=llm['provider'],
                        model=llm['model'],
                        api_key=llm['api_key'],
                        prompt=prompt,
                        endpoint=llm.get('endpoint'),
                        image_data=page_image_base64,
                        use_vision=use_vision
                    )
                    
                    # Capturar o resultado atual
                    step_result = {
                        'step': step_count,
                        'evaluation_previous_goal': llm_response
                    }
                    
                    # Analisar a resposta para identificar ações
                    # Versão melhorada que busca padrões de função como "function_name(params)"
                    import re
                    action_pattern = r'(\w+)\s*\(([^\)]*)\)'
                    action_matches = re.findall(action_pattern, llm_response)
                    
                    # Verificar se encontrou alguma ação
                    if action_matches:
                        for action_name, params_str in action_matches:
                            # Verificar se a ação é válida
                            if action_name in action_map:
                                # Processar os parâmetros
                                params = []
                                if params_str.strip():
                                    # Separar por vírgula, mas respeitar aspas
                                    import shlex
                                    try:
                                        # Adicionar vírgulas para que shlex entenda como tokens separados
                                        processed_str = params_str.replace(',', ' , ')
                                        tokens = shlex.split(processed_str)
                                        
                                        # Reconstruir os parâmetros
                                        current_param = ""
                                        for token in tokens:
                                            if token == ',':
                                                if current_param:
                                                    params.append(current_param.strip())
                                                    current_param = ""
                                            else:
                                                current_param += " " + token if current_param else token
                                        
                                        # Adicionar último parâmetro se existir
                                        if current_param:
                                            params.append(current_param.strip())
                                    except:
                                        # Se falhar, usar método mais simples
                                        params = [p.strip() for p in params_str.split(',')]
                                
                                # Executar a ação
                                action_func = action_map[action_name]
                                
                                step_result['next_goal'] = f"{action_name}({', '.join(params)})"
                                
                                try:
                                    # Chamada da função com parâmetros
                                    if len(params) == 0:
                                        action_result = await action_func()
                                    elif len(params) == 1:
                                        action_result = await action_func(params[0])
                                    elif len(params) == 2:
                                        action_result = await action_func(params[0], params[1])
                                    else:
                                        # Para mais parâmetros, provavelmente precisaria de ajuste específico
                                        action_result = await action_func(*params)
                                    
                                    # Adicionar resultado ao prompt
                                    prompt += f"\n\nAção: {action_name}({', '.join(params)})\nResultado: {action_result.extracted_content if action_result.success else action_result.error}"
                                    
                                    # Sair do loop de ações após a primeira ação
                                    break
                                except Exception as action_ex:
                                    error_msg = f"Erro ao executar {action_name}: {str(action_ex)}"
                                    result['errors'].append(error_msg)
                                    prompt += f"\n\nErro na ação {action_name}: {error_msg}"
                            elif action_name in controller.actions:
                                # Verificar se é uma ação do controller personalizado
                                logger.info(f"Executando ação personalizada: {action_name}")
                                
                                # Preparar parâmetros
                                action_params = {}
                                if params_str.strip():
                                    # Transformar string de parâmetros em dicionário
                                    # Este é um método simples; em uma versão completa você usaria um parser mais robusto
                                    import ast
                                    try:
                                        # Tentar avaliar como expressão Python
                                        eval_str = f"dict({params_str})"
                                        action_params = ast.literal_eval(eval_str)
                                    except:
                                        # Método mais simples: dividir por vírgula e por igual
                                        for param in params_str.split(','):
                                            if '=' in param:
                                                key, value = param.split('=', 1)
                                                action_params[key.strip()] = value.strip()
                                
                                # Desmascarar parâmetros se tiver dados sensíveis
                                if sensitive_data:
                                    for key, value in action_params.items():
                                        if isinstance(value, str):
                                            for placeholder, sensitive_value in sensitive_data.items():
                                                placeholder_pattern = f"[{placeholder}]"
                                                if placeholder_pattern in value:
                                                    action_params[key] = value.replace(placeholder_pattern, sensitive_value)
                                
                                # Executar a ação personalizada
                                browser_obj = {
                                    'get_current_page': lambda: tabs[current_tab_index]
                                }
                                action_result = await controller.execute_action(action_name, action_params, browser_obj)
                                
                                # Adicionar resultado ao prompt
                                prompt += f"\n\nAção personalizada: {action_name}({params_str})\nResultado: {action_result.extracted_content if action_result.success else action_result.error}"
                                
                                # Adicionar à lista de passos
                                step_result['next_goal'] = f"{action_name}({params_str})"
                                
                                # Sair do loop de ações após a primeira ação
                                break
                            else:
                                # Ação desconhecida
                                error_msg = f"Ação desconhecida: {action_name}"
                                result['errors'].append(error_msg)
                                prompt += f"\n\nErro: {error_msg}. Por favor, use uma ação válida."
                                continue
                    else:
                        # Se não houver ações claras, verificar se o agente concluiu a tarefa
                        completion_indicators = ['concluído', 'completo', 'finalizado', 'completada', 'terminada', 
                                               'finished', 'complete', 'done', 'completed', 'resultado final']
                        
                        if any(indicator in llm_response.lower() for indicator in completion_indicators):
                            result['output'] = llm_response
                            step_result['next_goal'] = "Tarefa concluída"
                            result['steps'].append(step_result)
                            result['status'] = 'finished'
                            break
                        else:
                            # Solicitar ação mais específica
                            prompt += "\n\nPor favor, indique uma ação específica a ser realizada. Use comandos como navigate(), click(), type(), etc."
                            continue
                    
                    # Capturar screenshot para referência se não já foi feito neste passo
                    if 'screenshot(' not in str(step_result.get('next_goal', '')):
                        await take_screenshot()
                    
                    # Registrar o passo
                    result['steps'].append(step_result)
                    
                except Exception as e:
                    error_msg = f"Erro no passo {step_count}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
                    
                    # Tentar continuar
                    prompt += f"\n\nOcorreu um erro: {error_msg}. Por favor, tente uma abordagem alternativa."
            
            # Se chegou ao limite de passos sem terminar
            if step_count >= max_steps and result['status'] == 'running':
                result['status'] = 'finished'
                result['output'] = "A tarefa atingiu o limite de passos. Avanço parcial registrado."
            
            # Ao final, quando for fechar o navegador, renomear o vídeo se necessário
            if recording_file:
                # Aguardar um pouco para garantir que o vídeo seja salvo
                await asyncio.sleep(1)
                
                # Obter os arquivos de vídeo gerados
                video_files = glob.glob(os.path.join(os.path.dirname(recording_file), "*.webm"))
                
                if video_files:
                    # Ordenar por data de modificação (o mais recente primeiro)
                    video_files.sort(key=os.path.getmtime, reverse=True)
                    
                    # Renomear o arquivo mais recente
                    if os.path.exists(recording_file):
                        os.remove(recording_file)
                    
                    shutil.move(video_files[0], recording_file)
                    logger.info(f"Vídeo renomeado para: {recording_file}")
            
            # Fechar o navegador
            await context.close()
            await browser.close()
    
    except Exception as e:
        logger.error(f"Erro geral na execução da tarefa {task_id}: {str(e)}")
        result['status'] = 'failed'
        result['errors'].append(f"Erro geral: {str(e)}")
    
    finally:
        # Limpar diretório temporário
        try:
            import shutil
            shutil.rmtree(temp_dir)
            logger.info(f"Diretório temporário removido: {temp_dir}")
        except Exception as e:
            logger.error(f"Erro ao remover diretório temporário: {str(e)}")
    
    return result