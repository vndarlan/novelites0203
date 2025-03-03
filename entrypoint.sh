#!/bin/bash
# Script de inicialização com foco na porta correta

# Exibir informações básicas
echo "====== INICIALIZANDO APLICAÇÃO ======"
echo "Data/Hora: $(date)"
echo "Diretório: $(pwd)"

# IMPORTANTE: Garantir que usamos a porta 8501 para o Streamlit
export PORT=8501
echo "Porta configurada para Streamlit: $PORT"

# Executar script de inicialização para preparar o banco de dados
echo "Executando init_app.py..."
python init_app.py

# Verificar conteúdo do diretório (para diagnóstico)
echo "Conteúdo do diretório atual:"
ls -la

# Iniciar Streamlit explicitamente na porta 8501
echo "Iniciando Streamlit na porta 8501..."
exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0