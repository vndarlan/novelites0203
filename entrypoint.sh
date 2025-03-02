#!/bin/bash
set -e

# Definir variáveis de ambiente padrão se não existirem
export PORT=${PORT:-8501}
export DEBUG=${DEBUG:-false}
export HEALTH_PORT=${HEALTH_PORT:-5000}

echo "Iniciando entrypoint.sh..."

# Inicializar a aplicação
echo "Executando init_app.py..."
python init_app.py

# Iniciar o servidor de healthcheck como um processo separado
echo "Iniciando servidor de healthcheck na porta $HEALTH_PORT..."
python health_server.py --port $HEALTH_PORT &

# Armazenar PID do processo de healthcheck
HEALTH_PID=$!
echo "Servidor de healthcheck iniciado com PID $HEALTH_PID"

# Verificar se o servidor de healthcheck está funcionando
echo "Aguardando servidor de healthcheck iniciar..."
sleep 3

# Tenta várias vezes até o healthcheck responder
for i in {1..5}; do
  if curl -s http://localhost:$HEALTH_PORT/health > /dev/null; then
    echo "Servidor de healthcheck respondendo em http://localhost:$HEALTH_PORT/health"
    break
  else
    echo "Tentativa $i: Servidor de healthcheck ainda não está respondendo"
    if [ $i -eq 5 ]; then
      echo "AVISO: Servidor de healthcheck não respondeu após 5 tentativas!"
    else
      sleep 1
    fi
  fi
done

# Iniciar o Streamlit
echo "Iniciando Streamlit na porta $PORT..."
streamlit run app.py --server.port=$PORT --server.enableCORS=false --server.enableXsrfProtection=false