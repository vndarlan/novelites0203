import uuid
import datetime
import pytz
import os
import base64

def generate_unique_id():
    """Gera um ID único para tarefas"""
    return uuid.uuid4().hex

def format_datetime(dt, format_str="%d/%m/%Y %H:%M:%S"):
    """Formata um objeto datetime para exibição"""
    if not dt:
        return "-"
    
    # Verificar o tipo de dt
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt)
        except ValueError:
            return dt
    
    # Converter para o fuso horário local se for timezone-aware
    if dt.tzinfo is not None:
        local_tz = pytz.timezone('America/Sao_Paulo')  # Ajuste para seu fuso horário
        dt = dt.astimezone(local_tz)
    
    return dt.strftime(format_str)

def get_status_color(status):
    """Retorna uma cor CSS baseada no status da tarefa"""
    colors = {
        'created': '#3498db',  # Azul
        'running': '#f39c12',  # Laranja
        'finished': '#2ecc71',  # Verde
        'failed': '#e74c3c'    # Vermelho
    }
    return colors.get(status, '#95a5a6')  # Cinza como padrão

def get_llm_models(provider):
    """Retorna os modelos disponíveis para um determinado provedor de LLM"""
    models = {
        'openai': [
            'gpt-4o',
            'gpt-4-turbo',
            'gpt-4-vision',
            'gpt-4',
            'gpt-3.5-turbo'
        ],
        'anthropic': [
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307',
            'claude-2.1',
            'claude-2.0',
            'claude-instant-1.2'
        ],
        'azure': [
            'gpt-4',
            'gpt-4-32k',
            'gpt-35-turbo',
            'gpt-35-turbo-16k'
        ],
        'gemini': [
            'gemini-pro',
            'gemini-ultra'
        ],
        'deepseek': [
            'deepseek-chat',
            'deepseek-coder'
        ],
        'ollama': [
            'llama2',
            'llama3',
            'mistral',
            'mixtral',
            'phi'
        ]
    }
    
    return models.get(provider, ['default-model'])

def ensure_directory_exists(directory_path):
    """Garante que o diretório existe, criando-o se necessário"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    return directory_path

def save_screenshot(image_data, task_id):
    """Salva um screenshot e retorna o caminho do arquivo"""
    # Garantir que o diretório existe
    screenshots_dir = ensure_directory_exists('static/screenshots')
    
    # Criar nome de arquivo único
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{task_id}_{timestamp}.png"
    filepath = os.path.join(screenshots_dir, filename)
    
    # Salvar a imagem
    with open(filepath, 'wb') as f:
        # Se a imagem estiver em base64
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            # Extrair apenas os dados após o prefixo
            base64_data = image_data.split(',')[1]
            f.write(base64.b64decode(base64_data))
        else:
            # Se for bytes diretos
            f.write(image_data)
    
    return filepath