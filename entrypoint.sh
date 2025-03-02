#!/bin/bash
# Script de inicialização simplificado e robusto

# Exibir informações sobre o ambiente
echo "====== INICIALIZANDO APLICAÇÃO ======"
echo "Data/Hora: $(date)"
echo "Diretório: $(pwd)"
echo "Usuário: $(whoami)"
echo "Python: $(python --version)"

# Definir variáveis de ambiente padrão
export PORT=${PORT:-8080}
export HEALTH_PORT=${HEALTH_PORT:-5000}
export DEBUG=${DEBUG:-false}

echo "Porta para Streamlit: $PORT"
echo "Porta para Healthcheck: $HEALTH_PORT"

# Executar o script de inicialização
echo "Executando init_app.py..."
python init_app.py

# Iniciar o servidor de healthcheck em background
echo "Iniciando servidor de healthcheck..."
python health_check_server.py &
HEALTH_PID=$!
echo "Servidor de healthcheck iniciado com PID $HEALTH_PID"

# Esperar um pouco
sleep 3

# Iniciar Streamlit
echo "Iniciando Streamlit na porta $PORT..."
streamlit run app.py --server.port=$PORT --server.enableCORS=false --server.enableXsrfProtection=false