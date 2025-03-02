import threading
import logging
import time
import socket
from flask import Flask, jsonify, request

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variável global para manter referência ao app Flask
flask_app = None

def is_port_in_use(port):
    """Verifica se uma porta está em uso"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def setup_healthcheck(port=5000):
    """Configura um endpoint de health check para o Railway"""
    global flask_app
    
    # Verificar se a porta já está em uso
    if is_port_in_use(port):
        logger.warning(f"Porta {port} já está em uso. Healthcheck pode já estar rodando.")
        return None
    
    logger.info(f"Configurando healthcheck na porta {port}")
    
    # Criar aplicativo Flask
    app = Flask(__name__)
    flask_app = app
    
    @app.route('/health')
    def health():
        logger.info(f"Recebida requisição de healthcheck em {request.path} de {request.remote_addr}")
        return jsonify({"status": "healthy"})
    
    @app.route('/')
    def root():
        logger.info(f"Recebida requisição na raiz de {request.remote_addr}")
        return jsonify({"status": "ok", "message": "API de healthcheck do Gerenciador de Agentes IA"})
    
    # Iniciar o servidor Flask em uma thread separada
    def run_flask():
        try:
            # Usar threaded=True para melhor performance e confiabilidade
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)
        except Exception as e:
            logger.error(f"Erro ao iniciar servidor Flask: {e}")
    
    thread = threading.Thread(target=run_flask)
    # Definir como non-daemon para garantir que o Flask continue rodando
    thread.daemon = False
    thread.start()
    
    # Esperar um pouco para garantir que o servidor tenha tempo de iniciar
    time.sleep(2)
    
    # Verificar se o servidor iniciou corretamente
    if is_port_in_use(port):
        logger.info(f"Servidor de healthcheck iniciado em http://0.0.0.0:{port}")
    else:
        logger.error(f"Falha ao iniciar servidor de healthcheck na porta {port}")
    
    return app