#!/bin/bash
set -e

# Definir variáveis de ambiente padrão se não existirem
export PORT=${PORT:-8501}
export DEBUG=${DEBUG:-false}

# Inicializar a aplicação
python init_app.py

# Iniciar o Streamlit
exec streamlit run app.py --server.port=$PORT --server.enableCORS=false --server.enableXsrfProtection=false