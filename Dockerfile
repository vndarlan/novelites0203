FROM python:3.10-slim

WORKDIR /app

# Instalar dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    wget \
    gnupg \
    curl \
    net-tools \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar apenas o arquivo de requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Playwright e o navegador Chromium
RUN python -m playwright install chromium --with-deps

# Criar diretórios necessários antes de copiar os arquivos
RUN mkdir -p static/screenshots

# Copiar o resto do código
COPY . .

# Tornar scripts executáveis
RUN chmod +x entrypoint.sh
RUN chmod +x health_check_server.py
RUN [ -f health_server.py ] && chmod +x health_server.py || echo "health_server.py não encontrado"

# Expor portas
EXPOSE 8080
EXPOSE 5000

# Configurar entrypoint
ENTRYPOINT ["./entrypoint.sh"]