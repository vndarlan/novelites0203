#!/bin/bash
# Script de inicialização corrigido

# Exibir informações básicas
echo "====== INICIALIZANDO APLICAÇÃO ======"
echo "Data/Hora: $(date)"
echo "Diretório: $(pwd)"

# Verificar variáveis de ambiente - muito importante usar PORT do Railway!
export PORT=${PORT:-8501}
echo "Porta configurada: $PORT"

# Não tentar criar diretórios que já existem
if [ ! -d "static/screenshots" ]; then
  mkdir -p static/screenshots
  echo "Diretório static/screenshots criado"
else
  echo "Diretório static/screenshots já existe"
fi

# Executar script de inicialização para preparar o banco de dados
echo "Executando init_app.py..."
python init_app.py

# Verificar conteúdo do diretório (para diagnóstico)
echo "Conteúdo do diretório atual:"
ls -la

# Esta é a linha crucial - importante usar a porta $PORT e 0.0.0.0
echo "Iniciando Streamlit na porta $PORT..."
exec streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false