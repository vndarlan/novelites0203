#!/bin/bash
set -e

# Definir variáveis de ambiente padrão se não existirem
export PORT=${PORT:-8501}
export DEBUG=${DEBUG:-false}

# Inicializar a aplicação
python init_app.py

# Iniciar o servidor de healthcheck em background
python -c "
import threading
from utils.health_check import setup_healthcheck
import time

# Configurar healthcheck na porta 5000 (ou qualquer outra porta disponível)
setup_healthcheck(port=5000)

# Manter o script em execução
print('Servidor de healthcheck iniciado em http://0.0.0.0:5000')
" &

# Aguardar um momento para o servidor de healthcheck iniciar
sleep 2

# Iniciar o Streamlit
exec streamlit run app.py --server.port=$PORT --server.enableCORS=false --server.enableXsrfProtection=false