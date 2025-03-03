#!/bin/bash
# Script de inicialização com diagnóstico avançado

echo "====== INICIALIZANDO APLICAÇÃO COM DIAGNÓSTICO AVANÇADO ======"
echo "Data/Hora: $(date)"
echo "Diretório: $(pwd)"
echo "Conteúdo do diretório:"
ls -la

# Verificar se app.py existe
if [ ! -f "app.py" ]; then
  echo "ERRO: app.py não encontrado!"
  # Listar arquivos .py disponíveis
  echo "Arquivos Python disponíveis:"
  find . -name "*.py" -type f | sort
  exit 1
fi

# Verificar instalação do Streamlit
echo "Verificando instalação do Streamlit:"
which streamlit || echo "ERRO: Streamlit não encontrado no PATH!"
streamlit --version || echo "ERRO: Não foi possível obter a versão do Streamlit!"

# Verificar requisitos
echo "Pacotes Python instalados:"
pip list | grep -E "streamlit|psycopg2|sqlalchemy|playwright"

# IMPORTANTE: Usar a porta 8501 para o Streamlit
export PORT=8501
echo "Porta configurada para Streamlit: $PORT"

# Executar script de inicialização para preparar o banco de dados
echo "Executando init_app.py..."
python init_app.py

# Verificar variáveis de ambiente importantes
echo "Variáveis de ambiente relevantes:"
env | grep -E "PORT|DATABASE|RAILWAY|PATH" | sort

# Iniciar Streamlit com redirecionamento de saída para logs
echo "Iniciando Streamlit na porta 8501..."
echo "Comando: streamlit run app.py --server.port=8501 --server.address=0.0.0.0"

# Executar com captura de logs e sem usar exec para ver erros
streamlit run app.py --server.port=8501 --server.address=0.0.0.0 > streamlit.log 2>&1
EXIT_CODE=$?

# Se houver erro, mostrar os logs
if [ $EXIT_CODE -ne 0 ]; then
  echo "ERRO: Streamlit falhou com código $EXIT_CODE"
  echo "Últimas 50 linhas do log:"
  tail -n 50 streamlit.log
  exit $EXIT_CODE
fi

# Se chegar aqui, mantenha o processo rodando
exec tail -f streamlit.log