#!/usr/bin/env python3
"""
Servidor de healthcheck standalone para o Railway.
Este servidor roda independentemente da aplicação Streamlit,
garantindo que o healthcheck esteja sempre disponível.
"""

import os
import logging
import argparse
from flask import Flask, jsonify, request

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(port=5000):
    """Cria e configura a aplicação Flask para healthcheck"""
    app = Flask(__name__)

    @app.route('/health')
    def health():
        logger.info(f"Requisição de healthcheck recebida em {request.path} de {request.remote_addr}")
        return jsonify({"status": "healthy"})

    @app.route('/')
    def root():
        logger.info(f"Requisição na raiz recebida de {request.remote_addr}")
        return jsonify({
            "status": "ok", 
            "message": "Servidor de healthcheck ativo",
            "port": port
        })

    return app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Servidor de healthcheck para Railway')
    parser.add_argument('--port', type=int, default=5000, help='Porta para o servidor (padrão: 5000)')
    args = parser.parse_args()

    port = int(os.environ.get('HEALTH_PORT', args.port))
    logger.info(f"Iniciando servidor de healthcheck na porta {port}")
    
    app = create_app(port)
    app.run(host='0.0.0.0', port=port, debug=False)