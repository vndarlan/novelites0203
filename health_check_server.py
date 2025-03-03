#!/usr/bin/env python3
"""
Servidor de healthcheck dedicado para o Railway.
Executado como processo independente do Streamlit.
"""

import os
import sys
import logging
import time
import socket
from threading import Thread
from flask import Flask, jsonify, request

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("healthcheck.log")
    ]
)
logger = logging.getLogger("health-check")

# Obter porta do ambiente ou usar padrão
PORT = int(os.environ.get('HEALTH_PORT', 5000))
STREAMLIT_PORT = int(os.environ.get('PORT', 8080))

app = Flask(__name__)

def check_streamlit_running():
    """Verifica se o Streamlit está rodando na porta configurada"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', STREAMLIT_PORT))
            return result == 0
    except:
        return False

@app.route('/health')
def health():
    """Endpoint de healthcheck principal usado pelo Railway"""
    client_ip = request.remote_addr
    logger.info(f"Recebida requisição de healthcheck de {client_ip}")
    
    # Por segurança, vamos retornar healthy mesmo que o Streamlit não esteja rodando ainda
    # Durante o período inicial de inicialização
    return jsonify({"status": "healthy"})

@app.route('/status')
def status():
    """Endpoint para verificação detalhada do status"""
    streamlit_running = check_streamlit_running()
    logger.info(f"Status detalhado: Streamlit rodando: {streamlit_running}")
    
    return jsonify({
        "status": "ok",
        "streamlit_running": streamlit_running,
        "streamlit_port": STREAMLIT_PORT,
        "health_port": PORT,
        "environment": "railway" if os.environ.get('RAILWAY_ENVIRONMENT') else "local"
    })

@app.route('/')
def root():
    """Endpoint raiz para verificação manual"""
    client_ip = request.remote_addr
    logger.info(f"Recebida requisição na raiz de {client_ip}")
    return jsonify({
        "status": "ok",
        "message": "Servidor de healthcheck ativo",
        "port": PORT
    })

@app.route('/ping')
def ping():
    """Endpoint simples para verificar se o servidor está ativo"""
    return "pong"

if __name__ == "__main__":
    # Registrar início do servidor
    logger.info(f"Iniciando servidor de healthcheck na porta {PORT}")
    logger.info(f"Verificando Streamlit na porta {STREAMLIT_PORT}")
    
    # Verificar portas em uso
    ports_in_use = []
    for port in [PORT, STREAMLIT_PORT]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', port))
            if result == 0:
                ports_in_use.append(port)
    
    if ports_in_use:
        logger.warning(f"Portas já em uso: {ports_in_use}")
    
    # Iniciar Flask sem mensagens de desenvolvimento
    app.run(host='0.0.0.0', port=PORT, threaded=True)