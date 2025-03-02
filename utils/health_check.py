import threading
import time
import logging
from flask import Flask, jsonify

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_healthcheck(port=5000):
    """Configura um endpoint de health check para o Railway"""
    logger.info(f"Configurando healthcheck na porta {port}")
    
    # Criar aplicativo Flask
    app = Flask(__name__)
    
    @app.route('/health')
    def health():
        return jsonify({"status": "healthy"})
    
    @app.route('/')
    def root():
        return jsonify({"status": "ok", "message": "API de healthcheck do Gerenciador de Agentes IA"})
    
    # Iniciar o servidor Flask em uma thread separada
    def run_flask():
        app.run(host='0.0.0.0', port=port)
    
    thread = threading.Thread(target=run_flask)
    thread.daemon = True
    thread.start()
    
    logger.info(f"Servidor de healthcheck iniciado em http://0.0.0.0:{port}")
    
    return app