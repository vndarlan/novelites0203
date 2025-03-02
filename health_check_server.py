#!/usr/bin/env python3
"""
Servidor de healthcheck dedicado para o Railway.
Executado como processo independente do Streamlit.
"""

import os
import sys
import logging
import time
from flask import Flask, jsonify, request

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("health-check")

# Obter porta do ambiente ou usar padrão
PORT = int(os.environ.get('HEALTH_PORT', 5000))

app = Flask(__name__)

@app.route('/health')
def health():
    """Endpoint de healthcheck principal usado pelo Railway"""
    client_ip = request.remote_addr
    logger.info(f"Recebida requisição de healthcheck de {client_ip}")
    return jsonify({"status": "healthy"})

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
    
    # Iniciar Flask sem mensagens de desenvolvimento
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', PORT, app, threaded=True)