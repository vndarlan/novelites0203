#!/bin/bash
set -e

# Definir variáveis de ambiente padrão se não existirem
export PORT=${PORT:-8501}
export DEBUG=${DEBUG:-false}

echo "Iniciando entrypoint.sh..."

# Inicializar a aplicação
echo "Executando init_app.py..."
python init_app.py

# Iniciar o servidor de healthcheck em background
echo "Iniciando servidor de healthcheck..."
python -c "
import threading
from utils.health_check import setup_healthcheck
import time

# Configurar healthcheck na porta 5000
setup_healthcheck(port=5000)

# Manter o script em execução
print('Servidor de healthcheck iniciado em http://0.0.0.0:5000')
" &

# Aguardar um momento para o servidor de healthcheck iniciar
echo "Aguardando servidor de healthcheck iniciar..."
sleep 5

# Iniciar o Streamlit com tratamento de erros melhorado
echo "Iniciando Streamlit na porta $PORT..."
streamlit run app.py --server.port=$PORT --server.enableCORS=false --server.enableXsrfProtection=false || {
    echo "ERRO: Falha ao iniciar o servidor Streamlit"
    echo "Verificando logs..."
    tail -n 100 /tmp/streamlit_error.log 2>/dev/null || echo "Nenhum log de erro encontrado"
    exit 1
}