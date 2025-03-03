#!/bin/bash
# Script de inicialização com logs adicionais

# Exibir informações sobre o ambiente
echo "====== INICIALIZANDO APLICAÇÃO ======"
echo "Data/Hora: $(date)"
echo "Diretório: $(pwd)"
echo "Usuário: $(whoami)"
echo "Python: $(python --version)"
echo "Conteúdo do diretório atual: $(ls -la)"

# Definir variáveis de ambiente padrão
export PORT=${PORT:-8080}
export HEALTH_PORT=${HEALTH_PORT:-5000}
export DEBUG=${DEBUG:-true}

echo "Porta para Streamlit: $PORT"
echo "Porta para Healthcheck: $HEALTH_PORT"
echo "DEBUG: $DEBUG"

# Executar o script de inicialização
echo "Executando init_app.py..."
python init_app.py

# Verificar se o PostgreSQL está acessível
echo "Verificando conexão com o banco de dados..."
python -c "
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.sql import text

db_url = os.environ.get('DATABASE_URL', '')
if not db_url:
    print('Variável DATABASE_URL não definida')
    sys.exit(1)

# Ajustar URL se necessário
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('Conexão com banco de dados OK')
except Exception as e:
    print(f'Erro ao conectar ao banco de dados: {e}')
    sys.exit(1)
"

# Iniciar o servidor de healthcheck em background com logs
echo "Iniciando servidor de healthcheck..."
python health_check_server.py > healthcheck_server.log 2>&1 &
HEALTH_PID=$!
echo "Servidor de healthcheck iniciado com PID $HEALTH_PID"

# Esperar um pouco e verificar se o servidor de healthcheck está respondendo
sleep 5
echo "Verificando se o servidor de healthcheck está respondendo..."
curl -v http://localhost:$HEALTH_PORT/health || echo "Falha ao verificar healthcheck"

# Iniciar Streamlit com logs mais detalhados
echo "Iniciando Streamlit na porta $PORT..."
streamlit run app.py --server.port=$PORT --server.enableCORS=false --server.enableXsrfProtection=false --server.headless=true