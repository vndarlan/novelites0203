#!/bin/bash
# Script de inicialização simplificado

# Exibir informações básicas
echo "====== INICIALIZANDO APLICAÇÃO ======"
echo "Data/Hora: $(date)"
echo "Diretório: $(pwd)"

# Verificar variáveis de ambiente
export PORT=${PORT:-8501}
echo "Porta configurada: $PORT"

# Criar diretórios necessários
mkdir -p static/screenshots
echo "Diretórios criados"

# Executar script de inicialização para preparar o banco de dados
echo "Executando init_app.py..."
python init_app.py

# Iniciar Streamlit
echo "Iniciando Streamlit na porta $PORT..."
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0